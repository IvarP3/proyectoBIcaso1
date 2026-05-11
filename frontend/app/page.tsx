import Link from 'next/link';

const moduleCards = [
  {
    name: 'Torre de Control SIO (Minería de Datos)',
    internal_name: 'mineria',
    description: 'Seguimiento operativo de mermas, siniestros y patrones de clientes, rutas y contratos.',
    status: 'Activo',
    href: '/modules/torre-control-sio'
  },
  {
    name: 'Margen de Contratos (Series de tiempo)',
    internal_name: 'forecast_operativo',
    description: 'Pronóstico mensual de ingresos y margen con horizonte táctico de 6 meses.',
    status: 'Activo',
    href: '/modules/forecast'
  },
  {
    name: 'Rentabilidad B2B (Econometría)',
    internal_name: 'econometria',
    description: 'Lectura econométrica para rentabilidad, escenarios y alertas presupuestarias.',
    status: 'Activo',
    href: '/modules/econometria'
  },
  {
    name: 'Asistente Inteligente (PLN)',
    internal_name: 'asistente_inteligente',
    description: 'Consulta inteligente sobre documentos, reportes y criterios operativos.',
    status: 'Activo',
    href: '/modules/asistente-inteligente'
  }
];

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero hero--split">
        <div className="hero-headline">
          <p className="eyebrow">Transfreezer · sistema web modular</p>
          <h1>Plataforma de decisión para pronóstico, análisis y automatización.</h1>
        </div>
        <div className="hero-aside">
          <p className="lead">
            Base inicial en Next.js para el usuario final, conectada a FastAPI y preparada para crecer por módulos sin romper la arquitectura.
          </p>
          <div className="hero-pills">
            <div className="hero-pill">
              <span className="pill-label">Módulos activos</span>
            <strong className="pill-value">4</strong>
            </div>
            <div className="hero-pill">
              <span className="pill-label">Módulos próximos</span>
              <strong className="pill-value">0</strong>
            </div>
            <div className="hero-pill">
              <span className="pill-label">Backend</span>
              <strong className="pill-value">FastAPI</strong>
            </div>
            <div className="hero-pill">
              <span className="pill-label">Frontend</span>
              <strong className="pill-value">Next.js</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <h2>Módulos comerciales</h2>
          <p>Los nombres visibles ya están listos para el usuario final.</p>
        </div>

        <div className="module-grid">
          {moduleCards.map((card) => (
            <Link key={card.name} href={card.href}>
              <article className="module-card" style={{ pointerEvents: card.status === 'Activo' ? 'auto' : 'none', opacity: card.status === 'Activo' ? 1 : 0.6 }}>
                <div className="module-top">
                  <h3>{card.name}</h3>
                  <span className={`status-badge status-${card.status.toLowerCase().replace(' ', '-')}`}>{card.status}</span>
                </div>
                <p>{card.description}</p>
                {card.status === 'Activo' && (
                  <div className="module-action">
                    <span>Acceder al módulo →</span>
                  </div>
                )}
              </article>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <h2>Próximos pasos</h2>
          <p>Accede al módulo <strong>Torre de Control SIO (Minería de Datos)</strong> para ver el análisis operativo con seguimiento de mermas, siniestros y señales de riesgo.</p>
        </div>
        <div className="cta-box">
          <p>La vista operativa está lista para centralizar alertas y trazabilidad sin tocar el backend de minería.</p>
          <Link href="/modules/torre-control-sio" className="btn-primary">
            Ver Torre de Control SIO →
          </Link>
        </div>
      </section>
    </main>
  );
}
