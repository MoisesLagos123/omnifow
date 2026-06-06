import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil, RotateCcw, Trash2 } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { Tabs, type TabItem } from "../../components/ui/Tabs";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import {
  sucursalesApi,
  type SucursalDetalle,
} from "../../api/sucursales";
import {
  describeError,
  extractSucursalEnUso,
} from "../../api/errorMessages";
import { ROUTES } from "../../routePaths";
import styles from "./SucursalesPages.module.css";

import { CajasTab } from "./CajasTab";
import { FoliosTab } from "./FoliosTab";

type TabValue = "general" | "cajas" | "folios";

export function SucursalDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("sucursal.gestionar");

  const [sucursal, setSucursal] = useState<SucursalDetalle | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [tab, setTab] = useState<TabValue>("general");
  const [confirmDeact, setConfirmDeact] = useState(false);
  const [enUsoModal, setEnUsoModal] = useState<{
    cajas: number;
    usuarios: number;
  } | null>(null);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoadError(null);
    sucursalesApi
      .obtenerSucursal(id, ctl.signal)
      .then(setSucursal)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, reloadTick]);

  function reload() {
    setReloadTick((t) => t + 1);
  }

  async function handleDeactivate() {
    if (!sucursal) return;
    setWorking(true);
    try {
      await sucursalesApi.desactivarSucursal(sucursal.id);
      toast.success("Sucursal desactivada", sucursal.nombre);
      reload();
    } catch (err) {
      const detalle = extractSucursalEnUso(err);
      if (detalle) {
        setEnUsoModal(detalle);
      } else {
        toast.error("No se pudo desactivar", describeError(err));
      }
    } finally {
      setWorking(false);
    }
  }

  async function handleReactivate() {
    if (!sucursal) return;
    setWorking(true);
    try {
      const actualizada = await sucursalesApi.reactivarSucursal(sucursal.id);
      toast.success("Sucursal reactivada", actualizada.nombre);
      reload();
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setWorking(false);
    }
  }

  const tabsItems = useMemo<TabItem[]>(() => {
    if (!sucursal) return [];
    return [
      {
        value: "general",
        label: "General",
        content: <GeneralTab sucursal={sucursal} />,
      },
      {
        value: "cajas",
        label: `Cajas (${sucursal.cajas.filter((c) => c.activo).length})`,
        content: (
          <CajasTab
            sucursalId={sucursal.id}
            initialCajas={sucursal.cajas}
            onChange={reload}
          />
        ),
      },
      {
        value: "folios",
        label: `Folios SII (${sucursal.rangos.filter((r) => r.activo).length})`,
        content: (
          <FoliosTab
            sucursalId={sucursal.id}
            initialRangos={sucursal.rangos}
            onChange={reload}
          />
        ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sucursal]);

  if (loadError) {
    return (
      <div className={styles.detail}>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.ADMIN_SUCURSALES)}
        >
          Volver a sucursales
        </Button>
        <ErrorAlert>{loadError}</ErrorAlert>
        <Button variant="ghost" onClick={reload}>
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.ADMIN_SUCURSALES)}
        >
          Volver a sucursales
        </Button>
      </div>

      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>
            {sucursal ? (
              <>
                {sucursal.nombre}
                <span className={styles.codeChip}>{sucursal.codigo}</span>
                {sucursal.activo ? (
                  <Badge variant="success">Activa</Badge>
                ) : (
                  <Badge variant="neutral">Inactiva</Badge>
                )}
              </>
            ) : (
              <Skeleton width={280} />
            )}
          </h1>
          <p className={styles.subtitle}>
            {sucursal ? (
              <span className={styles.mono}>{sucursal.rut_emisor}</span>
            ) : (
              <Skeleton width={160} />
            )}
          </p>
        </div>

        {sucursal && (
          <div className={styles.headerActions}>
            <RequirePermission code="sucursal.gestionar">
              <Button
                variant="ghost"
                leftIcon={<Pencil size={16} aria-hidden="true" />}
                onClick={() =>
                  navigate(ROUTES.ADMIN_SUCURSAL_EDITAR(sucursal.id))
                }
              >
                Editar
              </Button>
            </RequirePermission>
            {sucursal.activo
              ? canGestionar && (
                  <Button
                    variant="danger-ghost"
                    leftIcon={<Trash2 size={16} aria-hidden="true" />}
                    onClick={() => setConfirmDeact(true)}
                  >
                    Desactivar
                  </Button>
                )
              : canGestionar && (
                  <Button
                    leftIcon={<RotateCcw size={16} aria-hidden="true" />}
                    onClick={handleReactivate}
                    loading={working}
                  >
                    Reactivar
                  </Button>
                )}
          </div>
        )}
      </header>

      {sucursal ? (
        <Tabs
          items={tabsItems}
          value={tab}
          onChange={(v) => setTab(v as TabValue)}
          ariaLabel="Secciones de la sucursal"
        />
      ) : (
        <Skeleton height="300px" />
      )}

      <ConfirmDialog
        open={confirmDeact}
        onClose={() => setConfirmDeact(false)}
        title="Desactivar sucursal"
        description={
          sucursal
            ? `¿Confirmas que deseas desactivar "${sucursal.nombre}"? Podrás reactivarla más adelante.`
            : ""
        }
        confirmLabel="Desactivar"
        destructive
        onConfirm={handleDeactivate}
      />

      <ConfirmDialog
        open={enUsoModal !== null}
        onClose={() => setEnUsoModal(null)}
        title="No se puede desactivar"
        description={
          enUsoModal ? (
            <>
              <p>
                Esta sucursal está en uso y no puede desactivarse mientras
                tenga:
              </p>
              <ul style={{ paddingLeft: "1.25rem", margin: "0.5rem 0" }}>
                <li>
                  <strong>{enUsoModal.cajas}</strong>{" "}
                  {enUsoModal.cajas === 1 ? "caja activa" : "cajas activas"}
                </li>
                <li>
                  <strong>{enUsoModal.usuarios}</strong>{" "}
                  {enUsoModal.usuarios === 1
                    ? "usuario asignado"
                    : "usuarios asignados"}
                </li>
              </ul>
              <p>
                Desactiva las cajas y libera la asignación de usuarios antes de
                intentarlo de nuevo.
              </p>
            </>
          ) : null
        }
        confirmLabel="Entendido"
        cancelLabel="Cerrar"
        onConfirm={() => setEnUsoModal(null)}
      />
    </div>
  );
}

function GeneralTab({ sucursal }: { sucursal: SucursalDetalle }) {
  return (
    <Card>
      <dl className={styles.detailGrid}>
        <dt>Código</dt>
        <dd className={styles.mono}>{sucursal.codigo}</dd>
        <dt>Nombre</dt>
        <dd>{sucursal.nombre}</dd>
        <dt>RUT emisor</dt>
        <dd className={styles.mono}>{sucursal.rut_emisor}</dd>
        <dt>Dirección</dt>
        <dd>{sucursal.direccion ?? <em className={styles.muted}>—</em>}</dd>
        <dt>Comuna</dt>
        <dd>{sucursal.comuna ?? <em className={styles.muted}>—</em>}</dd>
        <dt>Región</dt>
        <dd>{sucursal.region ?? <em className={styles.muted}>—</em>}</dd>
        <dt>Estado</dt>
        <dd>
          {sucursal.activo ? (
            <Badge variant="success">Activa</Badge>
          ) : (
            <Badge variant="neutral">Inactiva</Badge>
          )}
        </dd>
      </dl>
    </Card>
  );
}

