import { useAuth } from "@/contexts/AuthContext";
import { Redirect } from "wouter";
import { Loader2 } from "lucide-react";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuth } = useAuth();

  if (!isAuth) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
}
