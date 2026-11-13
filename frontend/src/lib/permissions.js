export const ACTIONS = ["view", "create", "edit", "delete", "publish"];

export const MODULES = [
  { key: "pages", label: "Pages", group: "Content", actions: ACTIONS },
  { key: "books", label: "Catalogue", group: "Content", actions: ACTIONS },
  { key: "news", label: "News", group: "Content", actions: ACTIONS },
  { key: "careers", label: "Careers", group: "Content", actions: ACTIONS },
  { key: "tenders", label: "Tenders", group: "Content", actions: ACTIONS },
  { key: "resources", label: "Resources", group: "Content", actions: ACTIONS },
  { key: "enquiries", label: "Enquiries", group: "Audience", actions: ["view", "edit"] },
  { key: "subscribers", label: "Newsletter", group: "Audience", actions: ["view", "delete"] },
  { key: "settings", label: "Site settings", group: "System", actions: ["view", "edit"] },
  { key: "users", label: "Users", group: "System", actions: ["view", "create", "edit", "delete"] },
  { key: "activity", label: "Activity log", group: "System", actions: ["view"] },
  { key: "backup", label: "Backup & restore", group: "System", actions: ["view", "create", "delete"] },
  { key: "options", label: "Dropdown options", group: "System", actions: ACTIONS },
  { key: "media", label: "File uploads", group: "Content", actions: ["view", "create"] },
];

export const ACTION_LABELS = {
  view: "View",
  create: "Create",
  edit: "Edit",
  delete: "Delete",
  publish: "Publish",
};

const ALL = Object.fromEntries(MODULES.map((module) => [module.key, [...module.actions]]));

const ADMIN_DEFAULTS = {
  pages: ACTIONS,
  books: ACTIONS,
  news: ACTIONS,
  careers: ACTIONS,
  tenders: ACTIONS,
  resources: ACTIONS,
  enquiries: ["view", "edit"],
  subscribers: ["view", "delete"],
  settings: ["view", "edit"],
  users: ["view", "create", "edit", "delete"],
  activity: ["view"],
  backup: ["view", "create", "delete"],
  options: ACTIONS,
  media: ["view", "create"],
};

const EDITOR_DEFAULTS = {
  pages: ["view", "create", "edit"],
  books: ["view", "create", "edit"],
  news: ["view", "create", "edit"],
  careers: ["view", "create", "edit"],
  tenders: ["view", "create", "edit"],
  resources: ["view", "create", "edit"],
  enquiries: ["view"],
  subscribers: ["view"],
  media: ["view", "create"],
};

export const ROLE_DEFAULTS = {
  super_admin: ALL,
  admin: ADMIN_DEFAULTS,
  editor: EDITOR_DEFAULTS,
};

export const ROLE_LABELS = {
  super_admin: "Super Administrator",
  admin: "Administrator",
  editor: "Editor",
};

export function roleDefaults(role) {
  return ROLE_DEFAULTS[role] || EDITOR_DEFAULTS;
}

export function effectivePermissions(user) {
  if (!user || user.is_active === false || user.is_suspended) return {};
  if (user.role === "super_admin" || user.is_super_administrator) return ALL;
  if (user.permissions && typeof user.permissions === "object" && Object.keys(user.permissions).length) {
    return user.permissions;
  }
  return roleDefaults(user.role);
}

export function can(user, module, action = "view") {
  if (!user || user.is_active === false || user.is_suspended) return false;
  if (user.role === "super_admin" || user.is_super_administrator) return true;
  const permissions = effectivePermissions(user);
  return Boolean(permissions?.[module]?.includes(action));
}

export function canAny(user, module, actions = ["view"]) {
  return actions.some((action) => can(user, module, action));
}

export function moduleLabel(key) {
  return MODULES.find((module) => module.key === key)?.label || key;
}

export function actionLabel(key) {
  return ACTION_LABELS[key] || key;
}

export function firstAllowedPath(user) {
  const order = [
    ["pages", "/admin/pages"],
    ["books", "/admin/books"],
    ["news", "/admin/news"],
    ["careers", "/admin/careers"],
    ["tenders", "/admin/tenders"],
    ["resources", "/admin/resources"],
    ["enquiries", "/admin/enquiries"],
    ["subscribers", "/admin/subscribers"],
    ["settings", "/admin/settings"],
    ["users", "/admin/users"],
    ["activity", "/admin/activity"],
    ["backup", "/admin/backup"],
    ["options", "/admin/options"],
  ];
  return order.find(([module]) => can(user, module, "view"))?.[1] || "/admin/account";
}
