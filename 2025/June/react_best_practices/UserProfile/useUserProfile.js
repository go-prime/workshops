// UserProfile/useUserProfile.js
import { useEffect, useState } from 'react';

export function useUserProfile() {
  const [user, setUser] = useState({ name: '', email: '' });
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    async function fetchUser() {
      setLoading(true);
      // Simulate API call
      const fetchedUser = await new Promise((res) =>
        setTimeout(() => res({ name: 'Jane Doe', email: 'jane@example.com' }), 1000)
      );
      setUser(fetchedUser);
      setLoading(false);
    }

    fetchUser();
  }, []);

  const validate = () => {
    const errs = {};
    if (!user.name) errs.name = 'Name is required';
    if (!user.email.includes('@')) errs.email = 'Invalid email';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleChange = (e) => {
    setUser({ ...user, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    // Simulate API update
    console.log('Submitting:', user);
    alert('Profile updated!');
  };

  return {
    user,
    errors,
    loading,
    handleChange,
    handleSubmit,
  };
}
