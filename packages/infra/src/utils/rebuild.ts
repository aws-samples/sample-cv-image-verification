import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";

const getNewestMtime = (dir: string): number => {
  let newestMtime = 0;

  const processDir = (currentDir: string) => {
    const items = fs.readdirSync(currentDir);

    for (const item of items) {
      const itemPath = path.join(currentDir, item);
      const stats = fs.statSync(itemPath);

      // Update newest mtime if this file/dir is newer
      newestMtime = Math.max(newestMtime, stats.mtimeMs);

      // Recursively check subdirectories
      if (stats.isDirectory()) {
        processDir(itemPath);
      }
    }
  };

  processDir(dir);
  return newestMtime;
};

const hasSourceChanged = (sourcePath: string, buildPath: string): boolean => {
  if (!fs.existsSync(buildPath)) return true;

  const sourceNewestMtime = getNewestMtime(sourcePath);
  const buildNewestMtime = getNewestMtime(buildPath);

  return sourceNewestMtime > buildNewestMtime;
};

export const rebuildTargetDir = (
  sourcePath: string,
  buildPath: string,
  buildCommand: string
) => {
  if (hasSourceChanged(sourcePath, buildPath)) {
    console.log("Web Source code has changed, rebuilding...");
    try {
      console.log(`Executing build command: ${buildCommand}`);
      execSync(buildCommand, {
        stdio: "inherit",
        timeout: 300000, // 5 minute timeout
      });
      console.log("Build completed successfully");
    } catch (error) {
      console.error(
        "Build failed:",
        error instanceof Error ? error.message : String(error)
      );
      throw new Error(`Build command failed: ${buildCommand}`);
    }
  } else {
    console.log("Source code unchanged, skipping build");
  }
};
