// UserProfile/UserProfileContainer.jsx
import React from 'react';
import { useUserProfile } from './useUserProfile';
import { UserProfileForm } from './UserProfileForm';

export function UserProfileContainer() {
  const {
    user,
    errors,
    loading,
    handleChange,
    handleSubmit,
  } = useUserProfile();

  if (loading) return <p>Loading user profile...</p>;

  return (
    <div>
      <h2>Edit Profile</h2>
      <UserProfileForm
        user={user}
        errors={errors}
        onChange={handleChange}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
