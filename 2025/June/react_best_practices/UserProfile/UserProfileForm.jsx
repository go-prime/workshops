// UserProfile/UserProfileForm.jsx
import React from 'react';

export function UserProfileForm({ user, errors, onChange, onSubmit }) {
  return (
    <form onSubmit={(e) => e.preventDefault()}>
      <div>
        <label>Name:</label>
        <input
          name="name"
          value={user.name}
          onChange={onChange}
        />
        {errors.name && <p style={{ color: 'red' }}>{errors.name}</p>}
      </div>

      <div>
        <label>Email:</label>
        <input
          name="email"
          value={user.email}
          onChange={onChange}
        />
        {errors.email && <p style={{ color: 'red' }}>{errors.email}</p>}
      </div>

      <button onClick={onSubmit}>Save</button>
    </form>
  );
}
