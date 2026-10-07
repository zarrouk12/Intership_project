/**
 * M1 — Administration : organisation, sites, départements, utilisateurs et rôles.
 *
 * Toutes les données proviennent de l'API. Chaque action est conditionnée par la
 * permission correspondante, et le backend la revérifie : un bouton masqué ici reste
 * refusé côté serveur si quelqu'un appelle l'endpoint directement.
 */
import { useMemo, useState } from "react";

import { errorMessage } from "../api/client";
import {
  useCreateDepartment,
  useCreateRole,
  useCreateSite,
  useCreateUser,
  useDepartments,
  useOrganization,
  usePermissionCatalog,
  useRoleTemplates,
  useRoles,
  useSites,
  useUpdateUser,
  useUsers,
} from "../api/queries";
import type { RoleSummary, UserSummary } from "../api/types";
import { IconBuilding, IconCheck, IconKey, IconLock, IconPlus, IconUsers } from "../components/Icons";
import { Page, PageHeader } from "../components/Layout";
import { Badge, Card, ErrorState, Loading } from "../components/ui";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";

type Tab = "organisation" | "utilisateurs" | "roles";

const SCOPE_LABELS: Record<string, string> = {
  platform: "Plateforme",
  organization: "Organisation",
  site: "Site",
  department: "Département",
  own: "Contributions",
};

/* ====================================================================== organisation */

function OrganisationTab() {
  const { can } = useAuth();
  const { data: organization, isLoading } = useOrganization(can("organization.read"));
  const { data: sites } = useSites(can("site.read"));
  const { data: departments } = useDepartments(can("department.read"));

  const createSite = useCreateSite();
  const createDepartment = useCreateDepartment();
  const [siteForm, setSiteForm] = useState({ name: "", code: "", city: "", site_type: "" });
  const [deptForm, setDeptForm] = useState({ name: "", code: "", family: "", site_id: "" });
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <Loading />;

  return (
    <div className="stack">
      <Card title="Informations de l'entreprise">
        <div className="meta-strip">
          <div className="meta-item">
            <div className="meta-label">Raison sociale</div>
            <div className="meta-value">{organization?.name ?? "—"}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Code</div>
            <div className="meta-value">{organization?.code ?? "—"}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Secteur</div>
            <div className="meta-value">{organization?.industry ?? "—"}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Pays</div>
            <div className="meta-value">{organization?.country ?? "—"}</div>
          </div>
        </div>
        {organization?.description && (
          <p className="muted" style={{ marginBottom: 0, lineHeight: 1.7 }}>
            {organization.description}
          </p>
        )}
      </Card>

      {error && <ErrorState error={new Error(error)} />}

      <div className="grid grid-2-even">
        <Card title="Sites" subtitle={`${sites?.length ?? 0} implantations`}>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Site</th>
                  <th>Code</th>
                  <th>Ville</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {sites?.map((site) => (
                  <tr key={site.id}>
                    <td style={{ fontWeight: 500 }}>{site.name}</td>
                    <td className="muted">{site.code}</td>
                    <td className="muted">{site.city ?? "—"}</td>
                    <td className="muted">{site.site_type ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {can("site.manage") && (
            <form
              style={{ marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 16 }}
              onSubmit={async (event) => {
                event.preventDefault();
                setError(null);
                try {
                  await createSite.mutateAsync(siteForm);
                  setSiteForm({ name: "", code: "", city: "", site_type: "" });
                } catch (e) {
                  setError(errorMessage(e));
                }
              }}
            >
              <div className="form-grid">
                <div className="cell field">
                  <label htmlFor="site-name">Nom du site</label>
                  <input
                    id="site-name"
                    className="input"
                    required
                    value={siteForm.name}
                    onChange={(e) => setSiteForm({ ...siteForm, name: e.target.value })}
                  />
                </div>
                <div className="cell field">
                  <label htmlFor="site-code">Code</label>
                  <input
                    id="site-code"
                    className="input"
                    required
                    value={siteForm.code}
                    onChange={(e) => setSiteForm({ ...siteForm, code: e.target.value.toUpperCase() })}
                  />
                </div>
                <div className="cell field">
                  <label htmlFor="site-city">Ville</label>
                  <input
                    id="site-city"
                    className="input"
                    value={siteForm.city}
                    onChange={(e) => setSiteForm({ ...siteForm, city: e.target.value })}
                  />
                </div>
                <div className="cell field">
                  <label htmlFor="site-type">Type</label>
                  <input
                    id="site-type"
                    className="input"
                    placeholder="Production, R&D, Siège..."
                    value={siteForm.site_type}
                    onChange={(e) => setSiteForm({ ...siteForm, site_type: e.target.value })}
                  />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={createSite.isPending}>
                <IconPlus size={16} />
                Ajouter le site
              </button>
            </form>
          )}
        </Card>

        <Card title="Départements" subtitle={`${departments?.length ?? 0} départements`}>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Département</th>
                  <th>Code</th>
                  <th>Famille</th>
                  <th>Responsable</th>
                </tr>
              </thead>
              <tbody>
                {departments?.map((dept) => (
                  <tr key={dept.id}>
                    <td style={{ fontWeight: 500 }}>{dept.name}</td>
                    <td className="muted">{dept.code}</td>
                    <td className="muted">{dept.family ?? "—"}</td>
                    <td className="muted">{dept.head_name ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {can("department.manage") && (
            <form
              style={{ marginTop: 18, borderTop: "1px solid var(--border)", paddingTop: 16 }}
              onSubmit={async (event) => {
                event.preventDefault();
                setError(null);
                try {
                  await createDepartment.mutateAsync({
                    ...deptForm,
                    site_id: deptForm.site_id ? Number(deptForm.site_id) : null,
                  });
                  setDeptForm({ name: "", code: "", family: "", site_id: "" });
                } catch (e) {
                  setError(errorMessage(e));
                }
              }}
            >
              <div className="form-grid">
                <div className="cell field">
                  <label htmlFor="dept-name">Nom du département</label>
                  <input
                    id="dept-name"
                    className="input"
                    required
                    value={deptForm.name}
                    onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })}
                  />
                </div>
                <div className="cell field">
                  <label htmlFor="dept-code">Code</label>
                  <input
                    id="dept-code"
                    className="input"
                    required
                    value={deptForm.code}
                    onChange={(e) => setDeptForm({ ...deptForm, code: e.target.value.toUpperCase() })}
                  />
                </div>
                <div className="cell field">
                  <label htmlFor="dept-family">Famille métier</label>
                  <input
                    id="dept-family"
                    className="input"
                    placeholder="production, qualite, commercial..."
                    value={deptForm.family}
                    onChange={(e) => setDeptForm({ ...deptForm, family: e.target.value })}
                  />
                </div>
                <div className="cell field">
                  <label htmlFor="dept-site">Site de rattachement</label>
                  <select
                    id="dept-site"
                    className="select"
                    value={deptForm.site_id}
                    onChange={(e) => setDeptForm({ ...deptForm, site_id: e.target.value })}
                  >
                    <option value="">Aucun</option>
                    {sites?.map((site) => (
                      <option key={site.id} value={site.id}>
                        {site.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={createDepartment.isPending}>
                <IconPlus size={16} />
                Ajouter le département
              </button>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}

/* ====================================================================== utilisateurs */

function UserDrawer({
  user,
  roles,
  onClose,
}: {
  user: UserSummary | null;
  roles: RoleSummary[];
  onClose: () => void;
}) {
  const { can, user: me } = useAuth();
  const { data: departments } = useDepartments(can("department.read"));
  const { data: sites } = useSites(can("site.read"));
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const isNew = user === null;
  const [form, setForm] = useState({
    email: user?.email ?? "",
    full_name: user?.full_name ?? "",
    job_title: user?.job_title ?? "",
    password: "",
    is_active: user?.is_active ?? true,
    role_codes: user?.role_codes ?? [],
    department_names: user?.department_names ?? [],
    site_names: user?.site_names ?? [],
  });
  const [error, setError] = useState<string | null>(null);

  const departmentIds = useMemo(
    () => (departments ?? []).filter((d) => form.department_names.includes(d.name)).map((d) => d.id),
    [departments, form.department_names],
  );
  const siteIds = useMemo(
    () => (sites ?? []).filter((s) => form.site_names.includes(s.name)).map((s) => s.id),
    [sites, form.site_names],
  );

  const toggle = (key: "role_codes" | "department_names" | "site_names", value: string) =>
    setForm((prev) => ({
      ...prev,
      [key]: prev[key].includes(value) ? prev[key].filter((v) => v !== value) : [...prev[key], value],
    }));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      if (isNew) {
        await createUser.mutateAsync({
          email: form.email,
          full_name: form.full_name,
          job_title: form.job_title || null,
          password: form.password,
          role_codes: form.role_codes,
          department_ids: departmentIds,
          department_id: departmentIds[0] ?? null,
          site_ids: siteIds,
        });
      } else {
        await updateUser.mutateAsync({
          id: user.id,
          full_name: form.full_name,
          job_title: form.job_title || null,
          is_active: form.is_active,
          role_codes: form.role_codes,
          department_ids: departmentIds,
          site_ids: siteIds,
          ...(form.password ? { password: form.password } : {}),
        });
      }
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  const pending = createUser.isPending || updateUser.isPending;
  const isSelf = !isNew && me?.id === user.id;

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <form className="drawer" onSubmit={submit}>
        <div className="drawer-head">
          <div>
            <div className="card-title">{isNew ? "Nouvel utilisateur" : form.full_name}</div>
            <div className="card-sub">
              {isNew
                ? "Le compte est créé dans votre organisation, sans accès aux autres."
                : user.email}
            </div>
          </div>
        </div>

        <div className="drawer-body">
          {error && <ErrorState error={new Error(error)} />}

          <h3 className="section-title">Identité</h3>
          <div className="form-grid">
            {isNew && (
              <div className="cell field">
                <label htmlFor="u-email">Adresse e-mail</label>
                <input
                  id="u-email"
                  className="input"
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </div>
            )}
            <div className="cell field">
              <label htmlFor="u-name">Nom complet</label>
              <input
                id="u-name"
                className="input"
                required
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </div>
            <div className="cell field">
              <label htmlFor="u-job">Fonction</label>
              <input
                id="u-job"
                className="input"
                value={form.job_title}
                onChange={(e) => setForm({ ...form, job_title: e.target.value })}
              />
            </div>
            <div className="cell field">
              <label htmlFor="u-pwd">{isNew ? "Mot de passe" : "Nouveau mot de passe"}</label>
              <input
                id="u-pwd"
                className="input"
                type="password"
                required={isNew}
                minLength={8}
                placeholder={isNew ? "" : "Laisser vide pour ne pas changer"}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
              <span className="help">Huit caractères minimum.</span>
            </div>
          </div>

          {!isNew && can("user.disable") && (
            <label className={form.is_active ? "check on" : "check"} style={{ marginBottom: 18 }}>
              <input
                type="checkbox"
                checked={form.is_active}
                disabled={isSelf}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              <span>
                Compte actif
                {isSelf && (
                  <span className="muted"> — vous ne pouvez pas désactiver votre propre compte</span>
                )}
              </span>
            </label>
          )}

          <h3 className="section-title">Rôles</h3>
          <div className="form-grid">
            {roles.map((role) => (
              <label
                key={role.code}
                className={
                  form.role_codes.includes(role.code) ? "cell check on" : "cell check"
                }
              >
                <input
                  type="checkbox"
                  checked={form.role_codes.includes(role.code)}
                  onChange={() => toggle("role_codes", role.code)}
                />
                <span>
                  {role.label}
                  <span className="muted" style={{ display: "block", fontSize: 12 }}>
                    Périmètre {SCOPE_LABELS[role.scope_level]?.toLowerCase()} ·{" "}
                    {role.permission_codes.length} permissions
                  </span>
                </span>
              </label>
            ))}
          </div>

          <h3 className="section-title">Départements de rattachement</h3>
          <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
            Un rôle au périmètre départemental ne peut modifier que ces départements.
          </p>
          <div className="form-grid">
            {departments?.map((dept) => (
              <label
                key={dept.id}
                className={
                  form.department_names.includes(dept.name) ? "cell check on" : "cell check"
                }
              >
                <input
                  type="checkbox"
                  checked={form.department_names.includes(dept.name)}
                  onChange={() => toggle("department_names", dept.name)}
                />
                <span>{dept.name}</span>
              </label>
            ))}
          </div>

          <h3 className="section-title">Sites</h3>
          <div className="form-grid">
            {sites?.map((site) => (
              <label
                key={site.id}
                className={form.site_names.includes(site.name) ? "cell check on" : "cell check"}
              >
                <input
                  type="checkbox"
                  checked={form.site_names.includes(site.name)}
                  onChange={() => toggle("site_names", site.name)}
                />
                <span>{site.name}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="drawer-foot">
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
          <button type="submit" className="btn btn-primary" disabled={pending}>
            <IconCheck size={16} />
            {pending ? "Enregistrement..." : isNew ? "Créer l'utilisateur" : "Enregistrer"}
          </button>
        </div>
      </form>
    </>
  );
}

function UsersTab() {
  const { can } = useAuth();
  const { data: users, isLoading, error } = useUsers(can("user.read"));
  const { data: roles } = useRoles(can("role.read"));
  const [drawer, setDrawer] = useState<{ open: boolean; user: UserSummary | null }>({
    open: false,
    user: null,
  });

  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;

  return (
    <>
      <Card
        title="Utilisateurs"
        subtitle={`${users?.length ?? 0} comptes dans votre organisation`}
        action={
          can("user.create") ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setDrawer({ open: true, user: null })}
            >
              <IconPlus size={16} />
              Inviter un utilisateur
            </button>
          ) : undefined
        }
      >
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Rôle</th>
                <th>Périmètre</th>
                <th>Département</th>
                <th>Site</th>
                <th>Dernière connexion</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((user) => (
                <tr
                  key={user.id}
                  className={can("user.update") ? "clickable" : undefined}
                  onClick={can("user.update") ? () => setDrawer({ open: true, user }) : undefined}
                >
                  <td style={{ fontWeight: 500 }}>
                    {user.full_name}
                    <div className="muted" style={{ fontSize: 12.5 }}>
                      {user.email}
                    </div>
                  </td>
                  <td>
                    <div className="chips">
                      {user.role_labels.length ? (
                        user.role_labels.map((label) => (
                          <span className="chip-sm" key={label}>
                            {label}
                          </span>
                        ))
                      ) : (
                        <span className="muted">Aucun rôle</span>
                      )}
                    </div>
                  </td>
                  <td className="muted">{SCOPE_LABELS[user.scope_level] ?? user.scope_level}</td>
                  <td className="muted">{user.department_names.join(", ") || "—"}</td>
                  <td className="muted">{user.site_names.join(", ") || "—"}</td>
                  <td className="muted">{formatDate(user.last_login_at)}</td>
                  <td>
                    <Badge tone={user.is_active ? "badge-green" : "badge-grey"}>
                      {user.is_active ? "Actif" : "Désactivé"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {drawer.open && (
        <UserDrawer
          user={drawer.user}
          roles={roles ?? []}
          onClose={() => setDrawer({ open: false, user: null })}
        />
      )}
    </>
  );
}

/* ============================================================================= rôles */

function RoleDrawer({ onClose }: { onClose: () => void }) {
  const { can } = useAuth();
  const { data: catalog } = usePermissionCatalog(can("role.read"));
  const createRole = useCreateRole();
  const [form, setForm] = useState({
    code: "",
    label: "",
    description: "",
    scope_level: "organization",
    permission_codes: [] as string[],
  });
  const [error, setError] = useState<string | null>(null);

  const groups = useMemo(() => {
    const out = new Map<string, { code: string; label: string }[]>();
    (catalog ?? []).forEach((permission) => {
      const group = permission.group ?? "Autres";
      if (!out.has(group)) out.set(group, []);
      out.get(group)!.push({ code: permission.code, label: permission.label });
    });
    return [...out.entries()];
  }, [catalog]);

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <form
        className="drawer"
        onSubmit={async (event) => {
          event.preventDefault();
          setError(null);
          try {
            await createRole.mutateAsync(form);
            onClose();
          } catch (e) {
            setError(errorMessage(e));
          }
        }}
      >
        <div className="drawer-head">
          <div>
            <div className="card-title">Nouveau rôle</div>
            <div className="card-sub">
              Composé à partir des permissions ouvertes à votre organisation.
            </div>
          </div>
        </div>

        <div className="drawer-body">
          {error && <ErrorState error={new Error(error)} />}

          <div className="form-grid">
            <div className="cell field">
              <label htmlFor="r-code">Code technique</label>
              <input
                id="r-code"
                className="input"
                required
                pattern="[a-z0-9_]+"
                placeholder="referent_qualite"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value.toLowerCase() })}
              />
              <span className="help">Minuscules, chiffres et tirets bas uniquement.</span>
            </div>
            <div className="cell field">
              <label htmlFor="r-label">Libellé</label>
              <input
                id="r-label"
                className="input"
                required
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
              />
            </div>
            <div className="cell field">
              <label htmlFor="r-scope">Périmètre</label>
              <select
                id="r-scope"
                className="select"
                value={form.scope_level}
                onChange={(e) => setForm({ ...form, scope_level: e.target.value })}
              >
                <option value="organization">Organisation</option>
                <option value="site">Site</option>
                <option value="department">Département</option>
                <option value="own">Contributions personnelles</option>
              </select>
            </div>
            <div className="cell wide field">
              <label htmlFor="r-desc">Description</label>
              <textarea
                id="r-desc"
                className="textarea"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
          </div>

          <h3 className="section-title">
            Permissions ({form.permission_codes.length} sélectionnées)
          </h3>
          <div className="perm-groups">
            {groups.map(([group, permissions]) => (
              <div key={group}>
                <div className="perm-group-title">{group}</div>
                {permissions.map((permission) => {
                  const locked = permission.code === "platform.admin";
                  return (
                    <label
                      key={permission.code}
                      className={locked ? "perm-check locked" : "perm-check"}
                      title={locked ? "Permission réservée à la plateforme Medicacom" : permission.label}
                    >
                      <input
                        type="checkbox"
                        disabled={locked}
                        checked={form.permission_codes.includes(permission.code)}
                        onChange={() =>
                          setForm((prev) => ({
                            ...prev,
                            permission_codes: prev.permission_codes.includes(permission.code)
                              ? prev.permission_codes.filter((c) => c !== permission.code)
                              : [...prev.permission_codes, permission.code],
                          }))
                        }
                      />
                      <span>
                        <code style={{ fontSize: 11.5 }}>{permission.code}</code>
                        {locked && <IconLock size={12} style={{ marginLeft: 6, verticalAlign: -1 }} />}
                      </span>
                    </label>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        <div className="drawer-foot">
          <button type="button" className="btn" onClick={onClose}>
            Annuler
          </button>
          <button type="submit" className="btn btn-primary" disabled={createRole.isPending}>
            <IconCheck size={16} />
            {createRole.isPending ? "Création..." : "Créer le rôle"}
          </button>
        </div>
      </form>
    </>
  );
}

function RolesTab() {
  const { can } = useAuth();
  const { data: roles, isLoading, error } = useRoles(can("role.read"));
  const { data: templates } = useRoleTemplates(can("role.read"));
  const [drawer, setDrawer] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;

  const describe = (code: string) => templates?.find((t) => t.code === code)?.description;

  return (
    <>
      <Card
        title="Rôles et permissions"
        subtitle="Les rôles fournis par la plateforme ne sont pas modifiables ; créez un rôle personnalisé pour ajuster les droits."
        action={
          can("role.manage") ? (
            <button type="button" className="btn btn-primary" onClick={() => setDrawer(true)}>
              <IconPlus size={16} />
              Créer un rôle
            </button>
          ) : undefined
        }
      >
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Rôle</th>
                <th>Périmètre</th>
                <th>Permissions</th>
                <th>Utilisateurs</th>
                <th>Nature</th>
              </tr>
            </thead>
            <tbody>
              {roles?.map((role) => (
                <>
                  <tr
                    key={role.code}
                    className="clickable"
                    onClick={() => setExpanded(expanded === role.code ? null : role.code)}
                  >
                    <td style={{ fontWeight: 500 }}>
                      {role.label}
                      <div className="muted" style={{ fontSize: 12.5 }}>
                        {describe(role.code) ?? role.description ?? role.code}
                      </div>
                    </td>
                    <td className="muted">{SCOPE_LABELS[role.scope_level] ?? role.scope_level}</td>
                    <td className="num">{role.permission_codes.length}</td>
                    <td className="muted">{role.user_count}</td>
                    <td>
                      {role.is_platform ? (
                        <Badge tone="badge-amber">Plateforme</Badge>
                      ) : role.is_system ? (
                        <Badge tone="badge-grey">Système</Badge>
                      ) : (
                        <Badge tone="badge-teal">Personnalisé</Badge>
                      )}
                    </td>
                  </tr>
                  {expanded === role.code && (
                    <tr key={`${role.code}-detail`}>
                      <td colSpan={5} style={{ background: "#fbfdfc" }}>
                        <div className="chips">
                          {role.permission_codes.map((code) => (
                            <span className="chip-sm" key={code}>
                              {code}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {drawer && <RoleDrawer onClose={() => setDrawer(false)} />}
    </>
  );
}

/* =========================================================================== écran */

export default function Administration() {
  const { can, user } = useAuth();
  const [tab, setTab] = useState<Tab>("organisation");

  const tabs: { key: Tab; label: string; icon: typeof IconBuilding; visible: boolean }[] = [
    { key: "organisation", label: "Organisation", icon: IconBuilding, visible: can("organization.read") },
    { key: "utilisateurs", label: "Utilisateurs", icon: IconUsers, visible: can("user.read") },
    { key: "roles", label: "Rôles & permissions", icon: IconKey, visible: can("role.read") },
  ];
  const visibleTabs = tabs.filter((t) => t.visible);
  const active = visibleTabs.some((t) => t.key === tab) ? tab : visibleTabs[0]?.key;

  return (
    <>
      <PageHeader
        title="Administration"
        subtitle={`${user?.organization.name ?? ""} · sites, départements, utilisateurs et droits`}
      />
      <Page>
        <div className="tabs">
          {visibleTabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              className={active === key ? "tab active" : "tab"}
              onClick={() => setTab(key)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        {active === "organisation" && <OrganisationTab />}
        {active === "utilisateurs" && <UsersTab />}
        {active === "roles" && <RolesTab />}
      </Page>
    </>
  );
}
