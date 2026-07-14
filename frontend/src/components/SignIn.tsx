interface Props {
  onSignIn: () => void;
  onSignUp: () => void;
  error?: string | null;
}

export function SignIn({ onSignIn, onSignUp, error }: Props) {
  return (
    <div className="signin">
      <div className="signin__card">
        <div className="signin__logo" aria-hidden>
          ◆
        </div>
        <h1>
          <span className="topbar__accent">AI</span> News
        </h1>
        <p className="signin__tagline">
          Your AI briefing — search the news, get instant summaries and sentiment,
          and keep a personal feed of everything you've summarised.
        </p>
        <div className="signin__actions">
          <button className="btn btn--lg" onClick={onSignUp}>
            Create account
          </button>
          <button className="btn btn--ghost btn--lg" onClick={onSignIn}>
            I already have an account
          </button>
        </div>
        {error && <p className="alert signin__error">{error}</p>}
        <p className="signin__note">Secured by WorkOS AuthKit</p>
      </div>
    </div>
  );
}
