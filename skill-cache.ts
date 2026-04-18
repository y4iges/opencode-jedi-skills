import * as crypto from "node:crypto";
import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { type Plugin, tool } from "@opencode-ai/plugin";

const BASE_DIR = path.join(os.homedir(), ".local", "share", "opencode", "skill-cache");

interface CacheEntry {
  key: string;
  content: string;
  sourceFiles: string[];
  sourceMtimes: Record<string, string>;
  cachedAt: string;
}

function projectCacheDir(projectRoot: string): string {
  const hash = crypto
    .createHash("sha256")
    .update(projectRoot)
    .digest("hex")
    .slice(0, 12);
  return path.join(BASE_DIR, hash);
}

function keyToFile(key: string): string {
  const hash = crypto
    .createHash("sha256")
    .update(key)
    .digest("hex")
    .slice(0, 16);
  return `${hash}.json`;
}

async function readEntry(
  cacheDir: string,
  key: string
): Promise<CacheEntry | null> {
  // Normalize key: ensure backslashes are consistent
  const normalizedKey = key.replace(/\\/g, "/");
  const altKey = key.replace(/\//g, "\\");
  
  for (const tryKey of [key, normalizedKey, altKey]) {
    try {
      const raw = await fs.readFile(path.join(cacheDir, keyToFile(tryKey)), "utf8");
      return JSON.parse(raw);
    } catch {
      // try next
    }
  }
  return null;
}

async function writeEntry(cacheDir: string, entry: CacheEntry): Promise<void> {
  // Normalize key to use forward slashes for consistency
  const normalizedEntry = {
    ...entry,
    key: entry.key.replace(/\\/g, "/"),
  };
  await fs.mkdir(cacheDir, { recursive: true });
  await fs.writeFile(
    path.join(cacheDir, keyToFile(normalizedEntry.key)),
    JSON.stringify(normalizedEntry, null, 2),
    "utf8"
  );
}

async function getMtimes(
  sourceFiles: string[],
  projectRoot: string
): Promise<Record<string, string>> {
  const mtimes: Record<string, string> = {};
  for (let relPath of sourceFiles) {
    // Normalize to forward slashes
    relPath = relPath.replace(/\\/g, "/");
    try {
      const stat = await fs.stat(path.resolve(projectRoot, relPath));
      mtimes[relPath] = stat.mtime.toISOString();
    } catch {
      // file doesn't exist
    }
  }
  return mtimes;
}

async function checkStale(
  entry: CacheEntry,
  projectRoot: string
): Promise<{ stale: boolean; changedFiles: string[] }> {
  if (!entry.sourceFiles?.length) return { stale: false, changedFiles: [] };
  const changed: string[] = [];
  for (let relPath of entry.sourceFiles) {
    // Normalize to forward slashes
    relPath = relPath.replace(/\\/g, "/");
    try {
      const stat = await fs.stat(path.resolve(projectRoot, relPath));
      if (stat.mtime.toISOString() !== entry.sourceMtimes[relPath]) {
        changed.push(relPath);
      }
    } catch {
      changed.push(relPath);
    }
  }
  return { stale: changed.length > 0, changedFiles: changed };
}

function parseSourceFiles(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

const plugin: Plugin = async ({ directory }) => {
  const cacheDir = projectCacheDir(directory);

  return {
    tool: {
      skill_save: tool({
        description:
          "Cache an analysis result so it survives compaction and can be reused. Call after expensive analysis (jedi_tool, large file reads, etc).",
        args: {
          key: tool.schema
            .string()
            .describe(
              "Unique cache key using colon format: 'command:filepath' e.g. 'overview:src/bot.py'"
            ),
          content: tool.schema.string().describe("The content to cache"),
          sourceFiles: tool.schema
            .string()
            .optional()
            .describe(
              "Comma-separated source file paths (relative to project) to track for staleness via mtime"
            ),
        },
        async execute(args: {
          key: string;
          content: string;
          sourceFiles?: string;
        }) {
          const srcFiles = parseSourceFiles(args.sourceFiles);
          const mtimes = await getMtimes(srcFiles, directory);
          await writeEntry(cacheDir, {
            key: args.key,
            content: args.content,
            sourceFiles: srcFiles,
            sourceMtimes: mtimes,
            cachedAt: new Date().toISOString(),
          });
          const tracked =
            srcFiles.length > 0
              ? ` (${srcFiles.length} source files tracked for staleness)`
              : "";
          return `Cached "${args.key}"${tracked}`;
        },
      }),

      skill_read: tool({
        description:
          "Read a cached analysis result. Returns content if valid, STALE if source files changed since cache, or NOT_FOUND. Always check cache before running expensive analysis.",
        args: {
          key: tool.schema
            .string()
            .describe("The cache key to look up"),
        },
        async execute(args: { key: string }) {
          const entry = await readEntry(cacheDir, args.key);
          if (!entry) {
            return `NOT_FOUND: "${args.key}". Run the analysis and use skill_save to cache the result.`;
          }

          const { stale, changedFiles } = await checkStale(entry, directory);
          if (stale) {
            return `STALE: ${changedFiles.join(", ")} changed since cached at ${entry.cachedAt}. Re-run the analysis and skill_save to update.`;
          }

          return entry.content;
        },
      }),

      skill_list: tool({
        description:
          "List all cached analysis results with staleness status. Use to check what's already been analyzed.",
        args: {},
        async execute() {
          try {
            const files = await fs.readdir(cacheDir);
            const jsons = files.filter((f) => f.endsWith(".json"));
            if (!jsons.length) return "No cached results.";

            const lines: string[] = [];
            for (const file of jsons) {
              try {
                const raw = await fs.readFile(
                  path.join(cacheDir, file),
                  "utf8"
                );
                const entry: CacheEntry = JSON.parse(raw);
                const { stale } = await checkStale(entry, directory);
                const status = stale ? "STALE" : "OK";
                const date = entry.cachedAt.slice(0, 10);
                const sources =
                  entry.sourceFiles.length > 0
                    ? `, ${entry.sourceFiles.length} sources`
                    : "";
                lines.push(
                  `[${status}] "${entry.key}" (${date}${sources})`
                );
              } catch {
                // skip corrupt entries
              }
            }
            return lines.join("\n") || "No cached results.";
          } catch {
            return "No cached results.";
          }
        },
      }),

      skill_invalidate: tool({
        description: "Delete a cached result. Use when cache is stale and you want to force re-analysis.",
        args: {
          key: tool.schema.string().describe("The cache key to delete"),
        },
        async execute(args: { key: string }) {
          const normalizedKey = args.key.replace(/\\/g, "/");
          try {
            await fs.unlink(path.join(cacheDir, keyToFile(normalizedKey)));
            return `Deleted "${args.key}"`;
          } catch {
            return `NOT_FOUND: "${args.key}"`;
          }
        },
      }),
    },
  };
};

export default plugin;
