/**
 * AgriSense Authentication Service Abstraction Layer
 * Encapsulates backend API communication, session management, and Demo Mode handling.
 *
 * Phase 6: ONE consistent source of truth for the session token.
 * All protected requests must use AuthService.getToken() which reads the
 * stored 'agrisense_session_token' key from localStorage.
 * window.AgriState.token is NOT used; callers must not hard-code tokens.
 */
const AuthService = {
    /** Returns the current session token or null if not authenticated. */
    getToken() {
        return localStorage.getItem('agrisense_session_token') || null;
    },

    /** Returns a standard Authorization header object, or null if no token. */
    authHeaders() {
        const token = this.getToken();
        if (!token) return null;
        return { 'Authorization': `Bearer ${token}` };
    },

    // Standard Database Login
    async login(emailOrPhone, password) {
        const res = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone_or_email: emailOrPhone, password: password })
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            data.isDemo = false;
            if (data.session_token) {
                localStorage.setItem('agrisense_session_token', data.session_token);
            }
        }
        return data;
    },

    // Demo Mode Secure Authentication
    async demoLogin() {
        try {
            const res = await fetch('/api/v1/auth/demo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                data.isDemo = true;
                if (data.session_token) {
                    localStorage.setItem('agrisense_session_token', data.session_token);
                }
            }
            return data;
        } catch (error) {
            return { status: "error", message: "Demo login is unavailable or disabled." };
        }
    },

    // Farmer Account Registration
    async register(registerData) {
        const res = await fetch('/api/v1/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(registerData)
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            data.isDemo = false;
        }
        return data;
    },

    // Single Sign-On (SSO)
    async sso(provider, email, fullName) {
        const payload = {};
        if (email) payload.email = email;
        if (fullName) payload.full_name = fullName;

        const res = await fetch(`/api/v1/auth/sso/${provider}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            data.isDemo = false;
        }
        return data;
    },

    // Update Profile — Phase 6: uses stored token for Authorization header
    async updateProfile(profileData) {
        const token = this.getToken();
        if (!token) {
            return { status: 'error', message: 'Not authenticated' };
        }
        const res = await fetch('/api/v1/auth/profile/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(profileData)
        });
        return await res.json();
    }
};

window.AuthService = AuthService;
