/**
 * Unit tests for the pure front-end helpers.
 *
 * Run with: npm test  (which maps to `node --test tests`)
 * These run without a browser or a React test renderer, so they exercise the
 * formatting and permission logic that every page and dashboard screen uses.
 */
import assert from "node:assert/strict";
import test from "node:test";

import {
  formatDate,
  formatDateTime,
  money,
  pluralise,
  safeImagePath,
} from "../src/lib/format.js";
import {
  can,
  canAny,
  effectivePermissions,
  firstAllowedPath,
  roleDefaults,
} from "../src/lib/permissions.js";

test("formatDate formats real dates and tolerates bad input", () => {
  assert.match(formatDate("2026-01-05T10:00:00Z"), /2026/);
  assert.equal(formatDate(null), "");
  assert.equal(formatDate("not-a-date"), "not-a-date");
});

test("formatDateTime includes a time component", () => {
  const value = formatDateTime("2026-01-05T10:00:00Z");
  assert.match(value, /2026/);
  assert.match(value, /:/);
});

test("money renders Kenyan shillings and handles missing prices", () => {
  assert.equal(money(null), "Enquire");
  assert.equal(money(""), "Enquire");
  assert.equal(money("not a number"), "Enquire");
  assert.match(money(1250), /KSh/);
  assert.match(money(1250), /1,250/);
});

test("pluralise handles one and many", () => {
  assert.equal(pluralise(1, "book"), "1 book");
  assert.equal(pluralise(2, "book"), "2 books");
  assert.equal(pluralise(2, "person", "people"), "2 people");
});

test("safeImagePath keeps absolute URLs and normalises relative paths", () => {
  assert.equal(safeImagePath(""), "/assets/klb-logo-blue.png");
  assert.equal(safeImagePath("https://example.com/a.png"), "https://example.com/a.png");
  assert.equal(safeImagePath("/media/a.png"), "/media/a.png");
  assert.equal(safeImagePath("media/a.png"), "/media/a.png");
});

test("editor defaults cannot see system modules or delete content", () => {
  const editor = { role: "editor", is_active: true };
  assert.equal(can(editor, "pages", "view"), true);
  assert.equal(can(editor, "pages", "create"), true);
  assert.equal(can(editor, "pages", "delete"), false);
  assert.equal(can(editor, "pages", "publish"), false);
  assert.equal(can(editor, "settings", "view"), false);
  assert.equal(can(editor, "users", "view"), false);
  assert.equal(can(editor, "backup", "view"), false);
  assert.equal(can(editor, "enquiries", "view"), true);
  assert.equal(can(editor, "enquiries", "delete"), false);
});

test("administrators can manage enquiries, including delete", () => {
  const admin = { role: "admin", is_active: true };
  assert.equal(can(admin, "enquiries", "view"), true);
  assert.equal(can(admin, "enquiries", "edit"), true);
  assert.equal(can(admin, "enquiries", "delete"), true);
  assert.equal(can(admin, "settings", "edit"), true);
  assert.equal(can(admin, "activity", "view"), true);
});

test("super administrators and suspended accounts are handled", () => {
  const superAdmin = { role: "super_admin", is_active: true };
  assert.equal(can(superAdmin, "anything", "anything"), true);
  const suspended = { role: "admin", is_active: true, is_suspended: true };
  assert.deepEqual(effectivePermissions(suspended), {});
  assert.equal(can(suspended, "pages", "view"), false);
  assert.equal(can({ role: "admin", is_active: false }, "pages", "view"), false);
  assert.equal(can(null, "pages", "view"), false);
});

test("stored permissions override role defaults", () => {
  const user = {
    role: "editor",
    is_active: true,
    permissions: { pages: ["view"], books: ["view", "edit"] },
  };
  assert.equal(can(user, "pages", "edit"), false);
  assert.equal(can(user, "books", "edit"), true);
  assert.equal(canAny(user, "books", ["delete", "edit"]), true);
});

test("firstAllowedPath returns the first readable module", () => {
  assert.equal(firstAllowedPath({ role: "editor", is_active: true }), "/admin/pages");
  assert.equal(
    firstAllowedPath({
      role: "editor",
      is_active: true,
      permissions: { enquiries: ["view"] },
    }),
    "/admin/enquiries",
  );
  assert.equal(firstAllowedPath({ role: "editor", is_active: true, permissions: { pages: [] } }), "/admin/account");
});

test("role defaults expose the module shape the dashboard expects", () => {
  const defaults = roleDefaults("admin");
  assert.deepEqual(defaults.enquiries, ["view", "edit", "delete"]);
  assert.deepEqual(defaults.subscribers, ["view", "delete"]);
  assert.equal(roleDefaults("unknown"), roleDefaults("editor"));
});
