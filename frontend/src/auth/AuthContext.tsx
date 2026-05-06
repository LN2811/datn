/* eslint-disable react-refresh/only-export-components */
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
  loginAuthLoginPost,
  logoutAuthLogoutPost,
} from '../generated/sdk.gen';
import { api } from '../api/axios';

export type CurrentUser = {
  id: string;
  email: string;
  account_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  avatar_url?: string | null;
  is_active: boolean;
  is_superuser: boolean;
};

type AuthContextValue = {
  isCheckingAuth: boolean;
  user: CurrentUser | null;
  login: (email: string, password: string) => Promise<CurrentUser>;
  register: (email: string, password: string) => Promise<CurrentUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<CurrentUser | null>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const SESSION_HINT_KEY = 'loc-tracking-has-session';

export const getHomePathByRole = (user: Pick<CurrentUser, 'is_superuser'> | null) =>
  user?.is_superuser ? '/admin' : '/dashboard';

const readSessionHint = () => {
  if (typeof window === 'undefined') {
    return false;
  }

  try {
    return window.localStorage.getItem(SESSION_HINT_KEY) === '1';
  } catch {
    return false;
  }
};

const writeSessionHint = (hasSession: boolean) => {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    if (hasSession) {
      window.localStorage.setItem(SESSION_HINT_KEY, '1');
      return;
    }

    window.localStorage.removeItem(SESSION_HINT_KEY);
  } catch {
    // Ignore storage errors and keep auth flow functional.
  }
};

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
    account_name: typeof source.account_name === 'string' ? source.account_name : null,
    contact_email: typeof source.contact_email === 'string' ? source.contact_email : null,
    contact_phone: typeof source.contact_phone === 'string' ? source.contact_phone : null,
    avatar_url: typeof source.avatar_url === 'string' ? source.avatar_url : null,
    is_active: source.is_active,
    is_superuser: source.is_superuser,
  };
};

const getErrorMessage = (error: unknown): string => {
  if (!error || typeof error !== 'object') {
    return 'Yeu cau that bai. Vui long thu lai.';
  }

  const source = error as {
    detail?: unknown;
    response?: { data?: { detail?: unknown } };
  };

  if (typeof source.response?.data?.detail === 'string') {
    return source.response.data.detail;
  }

  if (typeof source.detail === 'string') {
    return source.detail;
  }

  return 'Yeu cau that bai. Vui long thu lai.';
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(() => readSessionHint());

  const refreshUser = useCallback(async (): Promise<CurrentUser | null> => {
    try {
      const response = await api.get('/users/me');
      const parsedUser = parseCurrentUser(response.data);
      setUser(parsedUser);
      writeSessionHint(Boolean(parsedUser));
      return parsedUser;
    } catch {
      setUser(null);
      writeSessionHint(false);
      return null;
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const bootstrap = async () => {
      if (!readSessionHint()) {
        if (isMounted) {
          setIsCheckingAuth(false);
        }
        return;
      }

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
        writeSessionHint(true);
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

  const register = useCallback(
    async (email: string, password: string): Promise<CurrentUser> => {
      try {
        await api.post('/auth/register', {
          email,
          password,
        });
        writeSessionHint(true);
      } catch (error) {
        writeSessionHint(false);
        throw new Error(getErrorMessage(error));
      }

      const currentUser = await refreshUser();
      if (!currentUser) {
        throw new Error('Dang ky thanh cong nhung khong lay duoc thong tin nguoi dung.');
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
      writeSessionHint(false);
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isCheckingAuth,
      user,
      login,
      register,
      logout,
      refreshUser,
    }),
    [isCheckingAuth, user, login, register, logout, refreshUser],
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
