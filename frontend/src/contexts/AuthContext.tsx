import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import {
  isAuthenticated,
  clearSession,
  updateActivity,
  getRemainingSessionTime,
  getUserData,
} from "@/lib/auth";
import { authAPI, type User, type UserRole } from "@/lib/api";
import { toast } from "sonner";

interface AuthContextType {
  isAuth: boolean;
  user: User | null;
  role: UserRole | null;
  isSuperAdmin: boolean;
  logout: () => void;
  checkAuth: () => void;
  refreshUser: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuth, setIsAuth] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  /**
   * Load user data from localStorage
   */
  const refreshUser = () => {
    const userData = getUserData<User>();
    setUser(userData);
  };

  /**
   * Derived role from user profile
   */
  const role: UserRole | null = user?.profile?.role ?? null;

  /**
   * Derived super admin status from user profile
   * Super admins have platform-level privileges (e.g., multi-org uploads)
   */
  const isSuperAdmin: boolean = user?.profile?.is_super_admin ?? false;

  const checkAuth = () => {
    const authenticated = isAuthenticated();
    setIsAuth(authenticated);
    if (authenticated) {
      refreshUser();
    } else {
      setUser(null);
    }
    return authenticated;
  };

  const logout = async () => {
    try {
      // Call server to clear HTTP-only cookies
      await authAPI.logout();
    } catch {
      // Server logout failed, but still clear local state
    }
    // Always clear local session data
    clearSession();
    setIsAuth(false);
    setUser(null);
    toast.info("Logged out successfully");
  };

  // Check authentication on mount
  useEffect(() => {
    checkAuth();
    setIsChecking(false);
  }, []);

  // Set up activity tracking
  useEffect(() => {
    if (!isAuth) return;

    // Update activity on user interactions
    const handleActivity = () => {
      if (isAuthenticated()) {
        updateActivity();
      } else {
        // Session expired
        setIsAuth(false);
        toast.error("Session expired. Please login again.");
      }
    };

    // Track various user activities
    const events = ["mousedown", "keydown", "scroll", "touchstart"];
    events.forEach((event) => {
      window.addEventListener(event, handleActivity);
    });

    // Check session validity every minute
    const intervalId = setInterval(() => {
      if (!isAuthenticated()) {
        setIsAuth(false);
        toast.error("Session expired due to inactivity");
      }
    }, 60000); // Check every minute

    // Show warning when session is about to expire (5 minutes remaining)
    const warningIntervalId = setInterval(() => {
      const remaining = getRemainingSessionTime();
      const fiveMinutes = 5 * 60 * 1000;

      if (
        remaining > 0 &&
        remaining <= fiveMinutes &&
        remaining > fiveMinutes - 60000
      ) {
        const minutes = Math.ceil(remaining / 60000);
        toast.warning(
          `Session will expire in ${minutes} minute${minutes > 1 ? "s" : ""}`,
          {
            duration: 10000,
          },
        );
      }
    }, 60000); // Check every minute

    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      clearInterval(intervalId);
      clearInterval(warningIntervalId);
    };
  }, [isAuth]);

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-cyan-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider
      value={{
        isAuth,
        user,
        role,
        isSuperAdmin,
        logout,
        checkAuth,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
