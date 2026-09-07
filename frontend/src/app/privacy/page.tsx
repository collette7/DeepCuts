import Navigation from '../components/Navigation';
import './page.scss';

export default function PrivacyPage() {
  return (
    <>
      <Navigation />
      <div className="page-container policy-page">
        <article className="container policy-content">
          <p className="policy-eyebrow">Privacy</p>
          <h1>Your listening trail stays yours.</h1>
          <p className="policy-intro">
            DeepCuts stores only the data needed to run your account, favorites, and search history.
          </p>

          <section>
            <h2>What we store</h2>
            <p>
              We store your email address, saved albums, and searches made while signed in. We do
              not store your password.
            </p>
          </section>

          <section>
            <h2>Music services and AI providers</h2>
            <p>
              Search terms and album names can be sent to Anthropic or Google for recommendations.
              Spotify and Discogs receive album lookup requests for artwork and listening links.
            </p>
          </section>

          <section>
            <h2>Retention and deletion</h2>
            <p>
              We keep account data until you delete your account. Account deletion removes your
              profile, favorites, and signed-in search history. Deleted data can remain in
              infrastructure backups until those backups expire.
            </p>
          </section>

          <section>
            <h2>Contact</h2>
            <p>
              Send privacy questions to <a href="mailto:contact@deepcuts.casa">contact@deepcuts.casa</a>.
            </p>
          </section>
        </article>
      </div>
    </>
  );
}
