import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import Loading from "../components/Loading.jsx";
import { Alert, Card, EmptyState, PageHead } from "./AdminUI.jsx";

export default function AdminTeamPhotos() {
  const { can } = useAuth();
  const editable = can("pages", "edit");
  const [state, setState] = useState({
    loading: true,
    pageSlug: null,
    sectionFound: false,
    members: [],
  });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyKey, setBusyKey] = useState("");
  const inputs = useRef({});

  useEffect(() => {
    load();
  }, []);

  async function load(showSpinner = true) {
    if (showSpinner) setState((current) => ({ ...current, loading: true }));
    try {
      const data = await admin.teamPhotos.list();
      setState({
        loading: false,
        pageSlug: data.page_slug,
        sectionFound: Boolean(data.section_found),
        members: data.members || [],
      });
    } catch (err) {
      setState((current) => ({ ...current, loading: false }));
      setError(err.message);
    }
  }

  async function handleFile(member, event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusyKey(member.key);
    setError("");
    setNotice("");
    try {
      const uploaded = await admin.upload(file);
      await admin.teamPhotos.update(member.key, { photo: uploaded.url });
      setNotice(`Photo saved for ${member.name}.`);
      await load(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey("");
      const input = inputs.current[member.key];
      if (input) input.value = "";
    }
  }

  async function removePhoto(member) {
    setBusyKey(member.key);
    setError("");
    setNotice("");
    try {
      await admin.teamPhotos.update(member.key, { photo: "" });
      setNotice(`Photo removed for ${member.name}.`);
      await load(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey("");
    }
  }

  return (
    <>
      <PageHead
        title="Team photos"
        lead="Upload a portrait for each card in the About page leadership section. Photos appear on the public team cards; cards stay complete with an initials placeholder when no photo is saved."
        actions={
          state.pageSlug ? (
            <Link className="btn btn--secondary" to={`/admin/pages/${state.pageSlug}/edit`}>
              Edit About page
            </Link>
          ) : null
        }
      />

      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>
      <Alert onClose={() => setNotice("")}>{notice}</Alert>

      {!editable ? (
        <Alert kind="warn">
          Your account can view the team but not edit the Pages module. Ask an administrator for edit permission to
          upload photos.
        </Alert>
      ) : null}

      {state.loading ? (
        <Loading label="Loading the leadership team…" />
      ) : !state.pageSlug ? (
        <EmptyState title="The About page was not found.">
          Create a page with the slug <span className="mono">about</span> and add a leadership section, then return
          here.
        </EmptyState>
      ) : !state.sectionFound ? (
        <EmptyState title="The leadership section was not found.">
          Open <Link to={`/admin/pages/${state.pageSlug}/edit`}>the About page</Link> and add a section containing a{" "}
          <span className="mono">team-grid</span> or <span className="mono">leadership-grid</span>.
        </EmptyState>
      ) : !state.members.length ? (
        <EmptyState title="No team cards were found.">
          Add team cards with a <span className="mono">data-member</span> key inside the leadership section, save the
          page, then return here.
        </EmptyState>
      ) : (
        <div className="team-admin-grid">
          {state.members.map((member) => (
            <Card className="team-admin-card" key={member.key}>
              <div className="team-admin-photo">
                {member.photo ? (
                  <img src={member.photo} alt={member.name} loading="lazy" />
                ) : (
                  <span aria-hidden="true">{member.initials}</span>
                )}
              </div>
              <div className="team-admin-body">
                <strong>{member.name || member.key}</strong>
                <p>{member.role || "Role not set"}</p>
                <div className="team-admin-actions">
                  <label className={`btn btn--secondary btn--sm${!editable || busyKey ? " is-disabled" : ""}`}>
                    {busyKey === member.key ? "Saving…" : member.photo ? "Replace photo" : "Upload photo"}
                    <input
                      ref={(element) => {
                        inputs.current[member.key] = element;
                      }}
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      hidden
                      disabled={!editable || Boolean(busyKey)}
                      onChange={(event) => handleFile(member, event)}
                    />
                  </label>
                  {member.photo ? (
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={() => removePhoto(member)}
                      disabled={!editable || Boolean(busyKey)}
                    >
                      Remove
                    </button>
                  ) : null}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
