import type { User } from "../types";

export type Tab = "briefing" | "saved";

interface Props {
  user: User;
  tab: Tab;
  onTab: (tab: Tab) => void;
  onSignOut: () => void;
}

export function TopBar({ user, tab, onTab, onSignOut }: Props) {
  const name = user.first_name || user.email || "Account";
  const initials = (user.first_name?.[0] || user.email?.[0] || "?").toUpperCase();

  return (
    <header className="topbar">
      <div className="topbar__brand">
        <span className="topbar__logo" aria-hidden>
          ◆
        </span>
        <span className="topbar__accent">AI</span> News
      </div>

      <nav className="tabs">
        <button
          className={`tab ${tab === "briefing" ? "tab--active" : ""}`}
          onClick={() => onTab("briefing")}
        >
          Briefing
        </button>
        <button
          className={`tab ${tab === "saved" ? "tab--active" : ""}`}
          onClick={() => onTab("saved")}
        >
          Saved
        </button>
      </nav>

      <div className="user">
        {user.profile_picture_url ? (
          <img className="user__avatar" src={user.profile_picture_url} alt="" />
        ) : (
          <span className="user__avatar user__avatar--initials" aria-hidden>
            {initials}
          </span>
        )}
        <span className="user__name">{name}</span>
        <button className="btn btn--ghost btn--small" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </header>
  );
}
