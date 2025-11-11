import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react'
import { User, AuthResponse, LoginCredentials, RegisterData } from '@/types'
import apiClient from '@/services/api'
import toast from 'react-hot-toast'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: User }
  | { type: 'AUTH_FAILURE'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'CLEAR_ERROR' }

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
}

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'AUTH_START':
      return {
        ...state,
        isLoading: true,
        error: null,
      }
    case 'AUTH_SUCCESS':
      return {
        ...state,
        user: action.payload,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      }
    case 'AUTH_FAILURE':
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload,
      }
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      }
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      }
    default:
      return state
  }
}

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>
  register: (userData: RegisterData) => Promise<void>
  logout: () => void
  clearError: () => void
  refreshToken: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState)

  const login = async (credentials: LoginCredentials) => {
    try {
      dispatch({ type: 'AUTH_START' })

      const response: AuthResponse = await apiClient.login(
        credentials.email,
        credentials.password
      )

      dispatch({ type: 'AUTH_SUCCESS', payload: response.user })
      toast.success('Welcome back!')
    } catch (error: any) {
      const errorMessage = error.response?.data?.error?.message || 'Login failed'
      dispatch({ type: 'AUTH_FAILURE', payload: errorMessage })
      toast.error(errorMessage)
    }
  }

  const register = async (userData: RegisterData) => {
    try {
      dispatch({ type: 'AUTH_START' })

      const user: User = await apiClient.register(userData)

      dispatch({ type: 'AUTH_SUCCESS', payload: user })
      toast.success('Account created successfully!')
    } catch (error: any) {
      const errorMessage = error.response?.data?.error?.message || 'Registration failed'
      dispatch({ type: 'AUTH_FAILURE', payload: errorMessage })
      toast.error(errorMessage)
    }
  }

  const logout = () => {
    apiClient.logout()
    dispatch({ type: 'LOGOUT' })
    toast.success('Logged out successfully')
  }

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' })
  }

  const refreshToken = async () => {
    try {
      await apiClient.refreshToken()
      // After successful refresh, get current user data
      const user = await apiClient.getCurrentUser()
      dispatch({ type: 'AUTH_SUCCESS', payload: user })
    } catch (error) {
      console.error('Token refresh failed:', error)
      dispatch({ type: 'LOGOUT' })
    }
  }

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const isValid = await apiClient.verifyToken()
        if (isValid) {
          const user = await apiClient.getCurrentUser()
          dispatch({ type: 'AUTH_SUCCESS', payload: user })
        }
      } catch (error) {
        // Token is invalid or expired
        dispatch({ type: 'LOGOUT' })
      }
    }

    checkAuth()
  }, [])

  const value: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    clearError,
    refreshToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}