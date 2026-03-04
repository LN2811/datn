import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  getCurrentUserAuthenCurrentUserGet,
  loginAuthLoginPost,
  logoutAuthLogoutPost,
} from '../generated/sdk.gen';

export type CurrentUser = {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
};

type AuthContextValue = {
  isCheckingAuth: boolean;
  user: CurrentUser | null;
  login: (email: string, password: string) => Promise<CurrentUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<CurrentUser | null>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const getHomePathByRole = (user: Pick<CurrentUser, 'is_superuser'> | null) =>
  user?.is_superuser ? '/admin' : '/dashboard';

const parseCurrentUser = (value: unknown): CurrentUser | null => {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const source = value as Record<string, unknown>;
  if (
    typeof source.id !== 'string' ||
    typeof source.email !== 'string' ||
    typeof source.is_active !== 'boolean' ||
    typeof source.is_superuser !== 'boolean'
  ) {
    return null;
  }

  return {
    id: source.id,
    email: source.email,
    is_active: source.is_active,
    is_superuser: source.is_superuser,
  };
};

const getErrorMessage = (error: unknown): string => {
  if (!error || typeof error !== 'object') {
    return 'Dang nhap that bai. Vui long thu lai.';
  }

  const source = error as { detail?: unknown };
  if (typeof source.detail === 'string') {
    return source.detail;
  }

  return 'Dang nhap that bai. Vui long thu lai.';
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  const refreshUser = useCallback(async (): Promise<CurrentUser | null> => {
    try {
      const data = await getCurrentUserAuthenCurrentUserGet({
        responseStyle: 'data',
        throwOnError: true,
      });
      const parsedUser = parseCurrentUser(data);
      setUser(parsedUser);
      return parsedUser;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const bootstrap = async () => {
      await refreshUser();
      if (isMounted) {
        setIsCheckingAuth(false);
      }
    };

    void bootstrap();

    return () => {
      isMounted = false;
    };
  }, [refreshUser]);

  const login = useCallback(
    async (email: string, password: string): Promise<CurrentUser> => {
      try {
        await loginAuthLoginPost({
          query: { email, password },
          responseStyle: 'data',
          throwOnError: true,
        });
      } catch (error) {
        throw new Error(getErrorMessage(error));
      }

      const currentUser = await refreshUser();
      if (!currentUser) {
        throw new Error('Dang nhap thanh cong nhung khong lay duoc thong tin nguoi dung.');
      }

      return currentUser;
    },
    [refreshUser],
  );

  const logout = useCallback(async () => {
    try {
      await logoutAuthLogoutPost({
        responseStyle: 'data',
        throwOnError: true,
      });
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isCheckingAuth,
      user,
      login,
      logout,
      refreshUser,
    }),
    [isCheckingAuth, user, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth phai duoc dung trong AuthProvider');
  }

  return context;
}
