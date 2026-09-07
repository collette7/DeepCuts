'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '../components/Navigation';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '@/lib/api';
import './page.scss';

export default function AccountPage() {
  const { user, loading, clearSession } = useAuth();
  const router = useRouter();
  const [isConfirming, setIsConfirming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace('/');
  }, [loading, router, user]);

  const handleDelete = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      await apiClient.deleteAccount();
      clearSession();
      router.replace('/');
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Account deletion failed.');
      setIsDeleting(false);
    }
  };

  if (loading || !user) return null;

  return (
    <>
      <Navigation />
      <div className="page-container account-page">
        <div className="container account-content">
          <p className="account-eyebrow">Account</p>
          <h1>{user.email}</h1>
          <p className="account-summary">
            Deleting your account removes your favorites and signed-in search history.
          </p>

          <section className="danger-zone">
            <h2>Delete account</h2>
            <p>This action is permanent. It cannot be undone.</p>
            {error && <p className="account-error" role="alert">{error}</p>}
            {isConfirming ? (
              <div className="account-actions">
                <button className="btn btn-secondary" onClick={() => setIsConfirming(false)} disabled={isDeleting}>
                  Cancel
                </button>
                <button className="btn account-delete-button" onClick={handleDelete} disabled={isDeleting}>
                  {isDeleting ? 'Deleting...' : 'Delete my account'}
                </button>
              </div>
            ) : (
              <button className="btn account-delete-button" onClick={() => setIsConfirming(true)}>
                Delete account
              </button>
            )}
          </section>
        </div>
      </div>
    </>
  );
}
