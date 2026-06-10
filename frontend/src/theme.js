import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    mode: 'light',
    background: {
      default: '#f6f8f1',
      paper: '#fffef9',
    },
    text: {
      primary: '#18212f',
      secondary: '#687385',
    },
    primary: {
      main: '#28b686',
      light: '#53d0a2',
      dark: '#137558',
      contrastText: '#18212f',
    },
    secondary: {
      main: '#67b7f7',
      light: '#9dd2fb',
      dark: '#2f80ed',
      contrastText: '#18212f',
    },
    error: { main: '#f97066' },
    warning: { main: '#f7c948' },
    success: { main: '#28b686' },
  },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
    h1: { fontFamily: '"Space Grotesk", "Inter", system-ui, sans-serif', fontWeight: 700 },
    h2: { fontFamily: '"Space Grotesk", "Inter", system-ui, sans-serif', fontWeight: 700 },
    h3: { fontFamily: '"Space Grotesk", "Inter", system-ui, sans-serif', fontWeight: 700 },
    h4: { fontFamily: '"Space Grotesk", "Inter", system-ui, sans-serif', fontWeight: 700 },
    h5: { fontFamily: '"Space Grotesk", "Inter", system-ui, sans-serif', fontWeight: 600 },
    h6: { fontFamily: '"Space Grotesk", "Inter", system-ui, sans-serif', fontWeight: 600 },
    button: { fontWeight: 700, textTransform: 'none' },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 700,
          transition: 'transform 150ms ease, box-shadow 150ms ease, background 150ms ease',
          '&:hover': {
            transform: 'translate(-1px, -1px)',
            boxShadow: '4px 4px 0 rgba(24, 33, 47, 0.16)',
          },
          '&:active': { transform: 'translate(0, 0)', boxShadow: 'none' },
        },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: '0 18px 45px rgba(24, 33, 47, 0.07)',
          border: '1px solid rgba(24, 33, 47, 0.11)',
          backgroundImage: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
        elevation1: { boxShadow: '0 18px 45px rgba(24, 33, 47, 0.07)' },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 700,
          fontFamily: '"Inter", system-ui, sans-serif',
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: '#f6f8f1', color: '#18212f' },
        'h1, h2, h3, h4, h5, h6': {
          fontFamily: '"Space Grotesk", "Inter", system-ui, sans-serif',
        },
      },
    },
  },
})

export default theme
