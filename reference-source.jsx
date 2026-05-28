// ROUND 2 — CONCEPT 1: Schichtkarte (Ticket)
// The mark is a number-ticket / deli-counter stub. Standdienst as the
// utility of distributing shift-tickets. Crimson on cream.

(function () {
  const C = {
    primary: '#a51f2c',
    primaryDeep: '#6c0d18',
    accent: '#e8b94a',
    bg: '#f5ece1',
    bgWarm: '#e9d8bd',
    soft: '#fdf6e9',
    ink: '#1a1311',
    sand: '#dbc8a8',
    muted: '#7a695a',
  };
  const fonts = {
    display: '"Hanken Grotesk", system-ui, sans-serif',
    body: '"Hanken Grotesk", system-ui, sans-serif',
    mono: '"Geist Mono", "IBM Plex Mono", ui-monospace, monospace',
  };

  function TicketMark({ size = 120, fg = C.primary, paper = C.soft, num = '14', accent = C.accent }) {
    const w = size * 0.78;
    const h = size;
    return (
      <svg viewBox="0 0 78 100" width={w} height={h} style={{ display: 'block' }}>
        <rect x="2" y="2" width="74" height="96" rx="6" fill={fg} />
        {/* perforation dashes */}
        <line x1="6" y1="30" x2="72" y2="30" stroke={paper} strokeWidth="1.2" strokeDasharray="2.5 2.5" />
        {/* SCHICHT label */}
        <text x="39" y="20" textAnchor="middle" fill={paper}
          fontFamily="Geist Mono, monospace" fontSize="7" letterSpacing="1.5">SCHICHT</text>
        {/* big number */}
        <text x="39" y="68" textAnchor="middle" fill={paper}
          fontFamily="Hanken Grotesk, sans-serif" fontWeight="700" fontSize="36" letterSpacing="-2">{num}</text>
        {/* accent dot */}
        <circle cx="39" cy="84" r="3" fill={accent} />
      </svg>
    );
  }

  function FaviconTicket({ size = 48, fg = C.primary, paper = C.soft }) {
    return (
      <svg viewBox="0 0 100 100" width={size} height={size} style={{ display: 'block' }}>
        <rect x="22" y="6" width="56" height="88" rx="8" fill={fg} />
        <line x1="28" y1="32" x2="72" y2="32" stroke={paper} strokeWidth="2" strokeDasharray="3 3" />
        <circle cx="50" cy="62" r="14" fill={paper} />
      </svg>
    );
  }

  function Wordmark({ size = 96, color = C.ink, rule = C.primary }) {
    return (
      <div style={{ display: 'inline-block', lineHeight: 0 }}>
        <span style={{
          fontFamily: fonts.display, fontSize: size, fontWeight: 700,
          letterSpacing: '-0.03em', color, lineHeight: 1,
        }}>Standdienst</span>
        <div style={{
          height: 0, borderTop: `${Math.max(2, size * 0.04)}px dashed ${rule}`,
          marginTop: size * 0.18,
        }} />
      </div>
    );
  }

  function Lockup({ size = 60, color = C.ink, fg = C.primary, paper = C.soft, accent = C.accent, rule = C.primary }) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: size * 0.36 }}>
        <TicketMark size={size * 1.5} fg={fg} paper={paper} accent={accent} />
        <Wordmark size={size * 1.05} color={color} rule={rule} />
      </div>
    );
  }

  function AppPreview() {
    return (
      <div style={{ padding: '24px 28px 32px', fontFamily: fonts.body, color: C.ink }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}>
          <Lockup size={16} />
          <div style={{ fontFamily: fonts.mono, fontSize: 11, color: C.muted, letterSpacing: '0.06em' }}>
            <span style={{ padding: '4px 10px', borderRadius: 4, background: C.bg }}>14. Juni '26</span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 22, alignItems: 'stretch', marginBottom: 18 }}>
          <TicketMark size={220} fg={C.primary} paper={C.soft} accent={C.accent} num="03" />
          <div style={{
            background: C.soft, borderRadius: 10, padding: '20px 22px',
            border: '1px solid ' + C.sand, display: 'flex', flexDirection: 'column', justifyContent: 'center',
          }}>
            <div style={{ fontFamily: fonts.mono, fontSize: 11, color: C.primary, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Deine nächste Schicht</div>
            <div style={{ fontFamily: fonts.display, fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1.1, marginTop: 6 }}>
              Bratwurstgrill A · 14–16 Uhr
            </div>
            <div style={{ fontSize: 13, color: C.muted, marginTop: 8 }}>
              gemeinsam mit Anna K. und Robert M. · Sommerfest TSV
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <button style={{ padding: '8px 14px', background: C.ink, color: C.soft, border: 'none', borderRadius: 4, fontFamily: fonts.body, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}>Anwesend melden</button>
              <button style={{ padding: '8px 14px', background: 'transparent', color: C.ink, border: '1px solid ' + C.sand, borderRadius: 4, fontFamily: fonts.body, fontSize: 12, cursor: 'pointer' }}>Tausch anfragen</button>
            </div>
          </div>
        </div>

        <div style={{ fontFamily: fonts.mono, fontSize: 10.5, color: C.muted, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 10, marginTop: 18 }}>Heute · offene Tickets</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {[
            { num: '07', t: '12–14', stand: 'Würstchen' },
            { num: '08', t: '14–16', stand: 'Würstchen' },
            { num: '12', t: '16–18', stand: 'Kuchen' },
            { num: '15', t: '18–20', stand: 'Pommes' },
          ].map((r, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <TicketMark size={120} fg={C.bg} paper={C.primary} accent={C.primary} num={r.num} />
              <div style={{ fontFamily: fonts.mono, fontSize: 11, color: C.ink }}>{r.t}</div>
              <div style={{ fontSize: 12, color: C.muted }}>{r.stand}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  function ConceptR2_01() {
    return (
      <BrandPage bg={C.bg} ink={C.ink} accent={C.primary} font={fonts.body} mono={fonts.mono} index="01" name="Schichtkarte">
        {/* HERO */}
        <div style={{ marginTop: 40, marginBottom: 80 }}>
          <div style={{ fontFamily: fonts.mono, fontSize: 12, color: C.primary, letterSpacing: '0.16em', textTransform: 'uppercase', marginBottom: 22 }}>R2 · 01 — die Karte</div>
          <Lockup size={92} />
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 64, marginTop: 36 }}>
            <div style={{ fontSize: 18, lineHeight: 1.55, color: C.ink, maxWidth: 620 }}>
              Das Bild kennt jeder: das Nummern-Ticket beim Bäcker, am Fleischwagen,
              an der Kuchentheke. Jede Schicht ist eine Karte mit Nummer.
              Wer eine zieht, übernimmt — eine Geste, die das Produkt direkt erklärt.
            </div>
            <div style={{ fontFamily: fonts.mono, fontSize: 11, color: C.muted, letterSpacing: '0.04em', lineHeight: 1.7 }}>
              <div style={{ color: C.ink, fontWeight: 600, marginBottom: 8 }}>Sprache</div>
              „eine Karte ziehen"<br />
              „die Karte abgeben"<br />
              „heute offen: 7 Karten"
            </div>
          </div>
        </div>

        <SectionHeader kicker="01 · Logo" title="Primärlogo und Varianten" mono={fonts.mono} ink={C.ink} accent={C.primary} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 60 }}>
          <div style={{ background: C.soft, borderRadius: 8, padding: '64px 48px', minHeight: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid ' + C.sand }}>
            <Lockup size={48} />
          </div>
          <div style={{ background: C.ink, borderRadius: 8, padding: '64px 48px', minHeight: 240, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Lockup size={48} color={C.soft} fg={C.primary} paper={C.soft} rule={C.soft} />
          </div>
          <div style={{ background: C.primary, borderRadius: 8, padding: '64px 48px', minHeight: 240, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Lockup size={48} color={C.soft} fg={C.soft} paper={C.primary} accent={C.accent} rule={C.soft} />
          </div>
          <div style={{ background: C.accent, borderRadius: 8, padding: '64px 48px', minHeight: 240, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Lockup size={48} color={C.ink} fg={C.primary} paper={C.soft} rule={C.ink} />
          </div>
        </div>

        <SectionHeader kicker="02 · Mark" title="Karte, App-Icon, Favicon" mono={fonts.mono} ink={C.ink} accent={C.primary} />
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1.2fr', gap: 18, marginBottom: 28 }}>
          <div style={{ background: C.soft, borderRadius: 8, padding: 36, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 320, border: '1px solid ' + C.sand }}>
            <TicketMark size={240} fg={C.primary} paper={C.soft} accent={C.accent} num="14" />
          </div>
          <div style={{ background: C.ink, borderRadius: 8, padding: 36, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 320 }}>
            <TicketMark size={240} fg={C.primary} paper={C.soft} accent={C.accent} num="03" />
          </div>
          <div style={{ background: C.bgWarm, borderRadius: 8, padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 320, gap: 18 }}>
            <div style={{ width: 180, height: 180, background: C.primary, borderRadius: 36, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FaviconTicket size={120} fg={C.soft} paper={C.primary} />
            </div>
            <div style={{ fontFamily: fonts.mono, fontSize: 10.5, color: C.muted, letterSpacing: '0.08em', textTransform: 'uppercase' }}>App-Icon</div>
          </div>
        </div>

        <div style={{ background: C.soft, borderRadius: 8, padding: '32px 40px', marginBottom: 60, border: '1px solid ' + C.sand }}>
          <FaviconStrip ink={C.ink} mono={fonts.mono} bg={C.bg}
            render={(s) => <FaviconTicket size={s * 0.95} fg={C.primary} paper={C.soft} />} />
        </div>

        <SectionHeader kicker="03 · Farbe" title="Palette" mono={fonts.mono} ink={C.ink} accent={C.primary} />
        <Palette ink={C.ink} mono={fonts.mono} swatches={[
          { name: 'Karmin', hex: '#a51f2c', fg: '#fff', label: 'Primary' },
          { name: 'Bordeaux', hex: '#6c0d18', fg: '#fff', label: 'Deep' },
          { name: 'Gold', hex: '#e8b94a', fg: '#1a1311', label: 'Accent' },
          { name: 'Sand', hex: '#dbc8a8', fg: '#1a1311', label: 'Surface' },
          { name: 'Papier', hex: '#fdf6e9', fg: '#1a1311', label: 'Background', border: '#dbc8a8' },
          { name: 'Tinte', hex: '#1a1311', fg: '#fdf6e9', label: 'Ink' },
        ]} />
        <div style={{ marginTop: 60 }} />

        <SectionHeader kicker="04 · Schrift" title="Hanken Grotesk & Geist Mono" mono={fonts.mono} ink={C.ink} accent={C.primary} />
        <div style={{ background: C.soft, borderRadius: 8, padding: '36px 40px', marginBottom: 60, border: '1px solid ' + C.sand }}>
          <TypeSpecimen display={fonts.display} body={fonts.body} mono={fonts.mono} ink={C.ink} accent={C.primary} />
        </div>

        <SectionHeader kicker="05 · Anwendung" title="Schicht-Ticket-Ansicht" mono={fonts.mono} ink={C.ink} accent={C.primary} />
        <AppFrame bg={C.bg} frame={C.bgWarm} ink={C.ink} mono={fonts.mono}>
          <AppPreview />
        </AppFrame>

        <div style={{ marginTop: 64, borderTop: '1px solid ' + C.sand, paddingTop: 28, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 36 }}>
          {[
            ['Stärken', 'Konkrete Metapher, sofort verstanden. Eigene Produkt-Sprache („eine Karte ziehen").'],
            ['Risiken', 'Nummern-Karten haben einen Wartezimmer-Klang — könnte zu nüchtern wirken.'],
            ['Anwendung', 'Echte Karten als Werbe-Geschenk. Tickets zum Ausdrucken am Eingang.'],
          ].map(([k, v]) => (
            <div key={k}>
              <div style={{ fontFamily: fonts.mono, fontSize: 10.5, color: C.primary, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 10 }}>{k}</div>
              <div style={{ fontSize: 13, color: C.ink, opacity: 0.8, lineHeight: 1.5 }}>{v}</div>
            </div>
          ))}
        </div>
      </BrandPage>
    );
  }

  window.ConceptR2_01 = ConceptR2_01;
})();
