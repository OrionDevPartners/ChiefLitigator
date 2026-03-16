"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"

interface Step1Props {
  onNext: () => void
}

export function Step1SignUp({ onNext }: Step1Props) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      onNext()
    }, 800)
  }

  const handleGoogle = () => {
    setGoogleLoading(true)
    setTimeout(() => {
      setGoogleLoading(false)
      onNext()
    }, 800)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-foreground text-balance">Create your account</h1>
        <p className="text-sm text-muted-foreground mt-1.5">No credit card required. Start free.</p>
      </div>

      {/* Google SSO */}
      <Button
        variant="outline"
        className="w-full h-11 border-border bg-surface-2 hover:bg-surface-3 text-foreground gap-2.5"
        onClick={handleGoogle}
        disabled={googleLoading}
        type="button"
      >
        {googleLoading ? (
          <span className="w-4 h-4 border-2 border-muted-foreground border-t-transparent rounded-full animate-spin" />
        ) : (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
            <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
          </svg>
        )}
        Continue with Google
      </Button>

      <div className="flex items-center gap-3">
        <Separator className="flex-1 bg-border" />
        <span className="text-xs text-muted-foreground">or</span>
        <Separator className="flex-1 bg-border" />
      </div>

      {/* Email form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email" className="text-sm text-foreground">Email address</Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="h-11 bg-surface-2 border-border text-foreground placeholder:text-muted-foreground focus-visible:ring-primary"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password" className="text-sm text-foreground">Password</Label>
          <Input
            id="password"
            type="password"
            placeholder="Min. 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="h-11 bg-surface-2 border-border text-foreground placeholder:text-muted-foreground focus-visible:ring-primary"
          />
        </div>

        <Button
          type="submit"
          className="w-full h-11 bg-primary text-primary-foreground hover:bg-primary/90 font-medium mt-1"
          disabled={loading}
        >
          {loading ? (
            <span className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
          ) : (
            "Create account"
          )}
        </Button>
      </form>

      <p className="text-xs text-center text-muted-foreground leading-relaxed">
        By creating an account you agree to our{" "}
        <a href="#" className="text-primary hover:underline">Terms of Service</a>{" "}
        and{" "}
        <a href="#" className="text-primary hover:underline">Privacy Policy</a>.
      </p>
    </div>
  )
}
