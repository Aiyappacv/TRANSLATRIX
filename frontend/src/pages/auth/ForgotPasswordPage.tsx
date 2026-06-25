import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Mail } from "lucide-react";
import { authApi } from "@/services/authApi";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const mutation = useMutation({ mutationFn: authApi.forgotPassword });
  return (
    <Card className="shadow-enterprise">
      <CardHeader><CardTitle>Forgot password</CardTitle><CardDescription>Enter your work email to receive a reset link.</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2"><Label>Email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <Button className="w-full" onClick={() => mutation.mutate(email)}><Mail className="h-4 w-4" />Send reset link</Button>
        {mutation.isSuccess ? <Alert tone="success">If the account exists, a password reset link has been sent.</Alert> : null}
        <Link className="block text-center text-sm text-primary" to="/auth/login">Back to login</Link>
      </CardContent>
    </Card>
  );
}
