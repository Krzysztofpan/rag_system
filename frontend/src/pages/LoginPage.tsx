import { type SubmitEvent, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/contexts/auth/AuthContext'

export default function LoginPage() {
    const { session, loading, signIn, signUp } = useAuth()
    const navigate = useNavigate()
    const [mode, setMode] = useState<'signIn' | 'signUp'>('signIn')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [notice, setNotice] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    if (loading) {
        return <div className="flex min-h-svh items-center justify-center text-sm text-muted-foreground">Loading…</div>
    }

    if (session) {
        return <Navigate to="/conversations" replace />
    }

    const handleSignUp = async () => {
        const { error: signUpError, needsEmailConfirmation } = await signUp(email, password)
        if (signUpError) {
            setError(signUpError)
            return
        }
        if (needsEmailConfirmation) {
            // No session yet, so navigating would only bounce off ProtectedRoute.
            setNotice(`Account created. Confirm ${email} to sign in.`)
            setMode('signIn')
            return
        }
        void navigate('/conversations', { replace: true })
    }

    const handleSignIn = async () => {
        const { error: signInError } = await signIn(email, password)
        if (signInError) {
            setError(signInError)
            return
        }
        void navigate('/conversations', { replace: true })
    }

    const handleSubmit = async () => {
        setError(null)
        setNotice(null)
        setSubmitting(true)
        try {
            await (mode === 'signIn' ? handleSignIn() : handleSignUp())
        }
        finally {
            setSubmitting(false)
        }
    }

    const onSubmit = (event: SubmitEvent<HTMLFormElement>) => {
        event.preventDefault()
        void handleSubmit()
    }

    return (
        <div className="flex min-h-svh items-center justify-center px-4">
            <title>Folio - Login</title>
            <form onSubmit={onSubmit} className="flex w-full max-w-sm flex-col gap-3">
                <h1 className="text-xl font-medium">{mode === 'signIn' ? 'Sign in' : 'Create account'}</h1>
                <p className="text-sm text-muted-foreground">Use your email and password to continue.</p>
                <Input type="email" placeholder="Email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
                <Input type="password" placeholder="Password" autoComplete={mode === 'signIn' ? 'current-password' : 'new-password'} value={password} onChange={(event) => setPassword(event.target.value)} required minLength={6} />
                {error
                    ? (
                            <p className="text-sm text-destructive" role="alert">
                                {error}
                            </p>
                        )
                    : null}
                {notice
                    ? (
                            <p className="text-sm text-muted-foreground" role="status">
                                {notice}
                            </p>
                        )
                    : null}
                <Button type="submit" disabled={submitting}>
                    {submitting ? 'Please wait…' : mode === 'signIn' ? 'Sign in' : 'Sign up'}
                </Button>
                <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                        setError(null)
                        setNotice(null)
                        setMode((current) => (current === 'signIn' ? 'signUp' : 'signIn'))
                    }}
                >
                    {mode === 'signIn' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
                </Button>
            </form>
        </div>
    )
}
