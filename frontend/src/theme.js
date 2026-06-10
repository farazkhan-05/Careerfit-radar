import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    mode: 'light',
    background: {
      default: '#F4F7FE',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#334155',
      secondary: '#64748b',
    },
    primary: {
      main: '#6366F1',
      light: '#818cf8',
      dark: '#4f46e5',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#22C55E',
      light: '#4ade80',
      dark: '#16a34a',
      contrastText: '#FFFFFF',
    },
    error: { main: '#f43f5e' },
    warning: { main: '#f59e0b' },
    success: { main: '#22C55E' },
  },
  typography: {
    fontFamily: '"Nunito", "Inter", system-ui, -apple-system, sans-serif',
    h1: { fontFamily: '"Poppins", system-ui, sans-serif', fontWeight: 700 },
    h2: { fontFamily: '"Poppins", system-ui, sans-serif', fontWeight: 700 },
    h3: { fontFamily: '"Poppins", system-ui, sans-serif', fontWeight: 600 },
    h4: { fontFamily: '"Poppins", system-ui, sans-serif', fontWeight: 600 },
    h5: { fontFamily: '"Poppins", system-ui, sans-serif', fontWeight: 600 },
    h6: { fontFamily: '"Poppins", system-ui, sans-serif', fontWeight: 600 },
    button: { fontWeight: 600, textTransform: 'none' },
  },
  shape: {
    borderRadius: 16,
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 50,
          textTransform: 'none',
          fontWeight: 600,
          transition: 'all 150ms ease',
          '&:hover': {
            transform: 'translateY(-1px)',
            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.25)',
          },
          '&:active': { transform: 'translateY(0)' },
        },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 10px 30px -10px rgba(99, 102, 241, 0.15)',
          border: '1px solid rgba(226, 232, 240, 0.8)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
        elevation1: { boxShadow: '0 10px 30px -10px rgba(99, 102, 241, 0.15)' },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 50,
          fontWeight: 600,
          fontFamily: '"Nunito", "Inter", sans-serif',
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: '#F4F7FE', color: '#334155' },
        'h1, h2, h3, h4, h5, h6': {
          fontFamily: '"Poppins", system-ui, sans-serif',
        },
      },
    },
  },
})

export default theme
