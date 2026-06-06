import { useState } from "react";

import { PageHeader } from "../../components/ui/PageHeader";
import { Tabs } from "../../components/ui/Tabs";
import { ResumenTab } from "./ResumenTab";
import { TopProductosTab } from "./TopProductosTab";
import styles from "./Reportes.module.css";

type TabValue = "resumen" | "top-productos";

export function ReportesPage() {
  const [tab, setTab] = useState<TabValue>("resumen");

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Finanzas"
        title="Reportes financieros"
        subtitle="Análisis de ingresos, utilidades, IVA y productos más vendidos."
      />

      <Tabs
        ariaLabel="Secciones de reportes"
        value={tab}
        onChange={(v) => setTab(v as TabValue)}
        items={[
          {
            value: "resumen",
            label: "Resumen financiero",
            content: <ResumenTab />,
          },
          {
            value: "top-productos",
            label: "Top productos",
            content: <TopProductosTab />,
          },
        ]}
      />
    </div>
  );
}
