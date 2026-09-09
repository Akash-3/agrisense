/**
 * AgriSense - Unified Email OTP Service
 * Encapsulates OTP dispatch, verification, email masking, and password strength checks.
 */

class EmailOTPService {
    constructor() {
        this.backendUrl = window.location.origin;
    }

    /**
     * Mask email address for security UI display (e.g. alex.vance@gmail.com -> a****e@gmail.com)
     */
    maskEmail(email) {
        if (!email || typeof email !== 'string') return 'User Account';
        const clean = email.trim();
        if (!clean.includes('@')) {
            // Mask phone or plain username
            if (clean.length <= 4) return '****';
            return clean.substring(0, 2) + '****' + clean.substring(clean.length - 2);
        }

        const parts = clean.split('@');
        const name = parts[0];
        const domain = parts[1];

        if (name.length <= 2) {
            return name[0] + '****@' + domain;
        }
        return name[0] + '****' + name[name.length - 1] + '@' + domain;
    }

    /**
     * Evaluate password strength score (0-100) and requirements
     */
    evaluatePasswordStrength(password) {
        if (!password) {
            return { score: 0, label: 'Weak', color: 'text-red-500', barColor: 'bg-slate-200', valid: false };
        }

        let score = 0;
        if (password.length >= 6) score += 25;
        if (password.length >= 8) score += 25;
        if (/[0-9]/.test(password)) score += 25;
        if (/[^A-Za-z0-9]/.test(password)) score += 25;

        if (score < 50) {
            return { score, label: 'Weak', color: 'text-red-500', barColor: 'bg-red-500', valid: password.length >= 6 };
        } else if (score < 100) {
            return { score, label: 'Medium', color: 'text-amber-500', barColor: 'bg-amber-500', valid: true };
        } else {
            return { score, label: 'Strong', color: 'text-emerald-600', barColor: 'bg-emerald-500', valid: true };
        }
    }

    /**
     * Send OTP for New Account Registration
     */
    async sendRegistrationOTP(email, fullName = "Farmer") {
        try {
            const resp = await fetch(`${this.backendUrl}/api/v1/auth/send-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_or_email: email, full_name: fullName })
            });
            const data = await resp.json();
            if (!resp.ok) {
                return { status: 'error', message: data.detail || data.message || 'Failed to send OTP code.' };
            }
            return { status: 'success', message: data.message || 'Verification code sent to email.' };
        } catch (e) {
            return { status: 'error', message: 'Network connection failure. Please try again.' };
        }
    }

    /**
     * Send OTP for Forgot Password (Login page)
     */
    async sendForgotPasswordOTP(email) {
        try {
            const resp = await fetch(`${this.backendUrl}/api/v1/auth/forgot-password/send-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_or_email: email })
            });
            const data = await resp.json();
            if (!resp.ok) {
                return { status: 'error', message: data.detail || data.message || 'No registered account found with that email.' };
            }
            return { status: 'success', message: data.message || 'Password reset code sent to email.' };
        } catch (e) {
            return { status: 'error', message: 'Network connection failure. Please try again.' };
        }
    }

    /**
     * Send OTP for Password Change (Profile page)
     */
    async sendPasswordChangeOTP(email, fullName = "Farmer") {
        try {
            const resp = await fetch(`${this.backendUrl}/api/v1/auth/password-change/send-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_or_email: email, full_name: fullName })
            });
            const data = await resp.json();
            if (!resp.ok) {
                return { status: 'error', message: data.detail || data.message || 'Failed to send password change code.' };
            }
            return { status: 'success', message: data.message || 'Password change code sent to email.' };
        } catch (e) {
            return { status: 'error', message: 'Network connection failure. Please try again.' };
        }
    }

    /**
     * Verify 6-digit OTP Code
     */
    async verifyOTP(email, otpCode) {
        try {
            const resp = await fetch(`${this.backendUrl}/api/v1/auth/verify-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_or_email: email, otp_code: otpCode })
            });
            const data = await resp.json();
            if (!resp.ok) {
                return { status: 'error', message: data.detail || data.message || 'Invalid or expired verification code.' };
            }
            return { status: 'success', message: 'OTP verified successfully!' };
        } catch (e) {
            return { status: 'error', message: 'Network connection failure.' };
        }
    }

    /**
     * Reset/Update Password with Verified OTP
     */
    async resetPassword(email, otpCode, newPassword) {
        try {
            const resp = await fetch(`${this.backendUrl}/api/v1/auth/forgot-password/reset`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_or_email: email, otp_code: otpCode, new_password: newPassword })
            });
            const data = await resp.json();
            if (!resp.ok) {
                return { status: 'error', message: data.detail || data.message || 'Failed to update password.' };
            }
            return { status: 'success', message: data.message || 'Password updated successfully!', password_updated_at: data.password_updated_at };
        } catch (e) {
            return { status: 'error', message: 'Network connection failure.' };
        }
    }
}

window.EmailOTPService = new EmailOTPService();
