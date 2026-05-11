export default function SettingsPage() {
  return (
    <main
      style={{
        minHeight: '100vh',
        padding: '2.5rem',
        background: 'linear-gradient(135deg, #0f1e2e 0%, #1a2a3a 60%, #1a2a3a 100%)',
        color: '#e0e6ed'
      }}
    >
      <section
        style={{
          maxWidth: '900px',
          border: '1px solid rgba(41, 128, 185, 0.26)',
          borderRadius: '14px',
          padding: '1.6rem',
          background: 'linear-gradient(135deg, rgba(27,79,114,0.14) 0%, rgba(41,128,185,0.08) 100%)'
        }}
      >
        <p style={{ margin: 0, fontSize: '0.8rem', color: '#7f8c8d', letterSpacing: '0.8px', textTransform: 'uppercase', fontWeight: 700 }}>
          Configuración
        </p>
        <h1 style={{ margin: '0.4rem 0 0.9rem 0', fontSize: '1.9rem', color: '#aed6f1' }}>
          Esta sección está en desarrollo
        </h1>
        <p style={{ margin: 0, color: '#b9c7d6', lineHeight: 1.55 }}>
          Estamos trabajando en las opciones de configuración del sistema.
        </p>
      </section>
    </main>
  );
}