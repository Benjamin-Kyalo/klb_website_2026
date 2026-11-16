#!/usr/bin/env node
/**
 * Parse every source file with esbuild.
 *
 * This project does not ship a full ESLint config, so `npm run lint` used to
 * fail with "eslint is not installed". This script gives the script a real,
 * useful meaning: it fails the build on any JavaScript or JSX syntax error in
 * frontend/src. esbuild is already installed as part of Vite.
 */
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { transform } from "esbuild";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourceDir = path.join(root, "src");
const extensions = new Set([".js", ".jsx"]);

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await walk(full)));
    else if (extensions.has(path.extname(entry.name))) files.push(full);
  }
  return files;
}

const files = await walk(sourceDir);
const failures = [];

for (const file of files) {
  const source = await readFile(file, "utf8");
  try {
    await transform(source, {
      loader: path.extname(file) === ".jsx" ? "jsx" : "js",
      jsx: "automatic",
      sourcefile: file,
    });
  } catch (error) {
    failures.push({ file, message: error.message });
  }
}

if (failures.length) {
  for (const failure of failures) {
    console.error(`\n${path.relative(root, failure.file)}`);
    console.error(failure.message);
  }
  console.error(`\n${failures.length} file(s) failed to parse.`);
  process.exit(1);
}

console.log(`Parsed ${files.length} source files with esbuild. No syntax errors.`);
