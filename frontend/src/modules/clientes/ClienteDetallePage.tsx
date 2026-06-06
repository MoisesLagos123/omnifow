import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil, RotateCcw, Trash2, Wallet } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission } from "../../auth/usePermission";
import { clientesApi, type Cliente } from "../../api/clientes";
import { describeError } from "../../api/errorMessages";
import { formatearRut } from "../administracion/rut";
import { ROUTES } from "../../routePaths";
import styles from "./ClientesPages.module.css";

export function ClienteDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("cliente.gestionar");

  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [confirmDeact, setConfirmDeact] = useState(false);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoadError(null);
    clientesApi
      .obtenerCliente(id, ctl.signal)
      .then(setCliente)
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
    if (!cliente) return;
    setWorking(true);
    try {
      await clientesApi.desactivarCliente(cliente.id);
      toast.success("Cliente desactivado", cliente.razon_social);
      reload();
    } catch (err) {
      toast.error("No se pudo desactivar", describeError(err));
    } finally {
      setWorking(false);
    }
  }

  async function handleReactivate() {
    if (!cliente) return;
    setWorking(true);
    try {
      const actualizado = await clientesApi.reactivarCliente(cliente.id);
      toast.success("Cliente reactivado", actualizado.razon_social);
      reload();
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setWorking(false);
    }
  }

  if (loadError) {
    return (
      <div className={styles.detail}>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate(ROUTES.CLIENTES)}
        >
          Volver a clientes
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
          onClick={() => navigate(ROUTES.CLIENTES)}
        >
          Volver a clientes
        </Button>
      </div>

      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>
            {cliente ? (
              <>
                {cliente.razon_social}
                <span className={styles.codeChip}>
                  {formatearRut(cliente.rut)}
                </span>
                {cliente.activo ? (
                  <Badge variant="success">Activo</Badge>
                ) : (
                  <Badge variant="neutral">Inactivo</Badge>
                )}
              </>
            ) : (
              <Skeleton width={280} />
            )}
          </h1>
        </div>

        {cliente && (
          <div className={styles.headerActions}>
            <RequirePermission code="cliente.gestionar">
              <Button
                variant="ghost"
                leftIcon={<Pencil size={16} aria-hidden="true" />}
                onClick={() => navigate(ROUTES.CLIENTE_EDITAR(cliente.id))}
              >
                Editar
              </Button>
            </RequirePermission>
            {cliente.activo
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

      {cliente ? (
        <Card>
          <dl className={styles.detailGrid}>
            <dt>RUT</dt>
            <dd className={styles.mono}>{formatearRut(cliente.rut)}</dd>
            <dt>Razón social</dt>
            <dd>{cliente.razon_social}</dd>
            <dt>Giro</dt>
            <dd>{cliente.giro ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Dirección</dt>
            <dd>{cliente.direccion ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Comuna</dt>
            <dd>{cliente.comuna ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Región</dt>
            <dd>{cliente.region ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Email</dt>
            <dd>{cliente.email ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Teléfono</dt>
            <dd>{cliente.telefono ?? <em className={styles.muted}>—</em>}</dd>
            <dt>Estado</dt>
            <dd>
              {cliente.activo ? (
                <Badge variant="success">Activo</Badge>
              ) : (
                <Badge variant="neutral">Inactivo</Badge>
              )}
            </dd>
          </dl>
        </Card>
      ) : (
        <Skeleton height="300px" />
      )}

      {/* Estado de cuenta — placeholder. TODO: habilitar con el módulo de
          Cuentas por Cobrar (CxC). No implementar hasta entonces. */}
      <section aria-labelledby="estado-cuenta-title">
        <h2 id="estado-cuenta-title" className={styles.sectionTitle}>
          Estado de cuenta
        </h2>
        <div className={styles.placeholderCard} aria-disabled="true">
          <p className={styles.placeholderTitle}>
            <Wallet size={18} aria-hidden="true" />
            Próximamente
          </p>
          <p className={styles.placeholderText}>
            Disponible cuando se habilite el módulo de Cuentas por Cobrar.
          </p>
        </div>
      </section>

      <ConfirmDialog
        open={confirmDeact}
        onClose={() => setConfirmDeact(false)}
        title="Desactivar cliente"
        description={
          cliente
            ? `¿Confirmas que deseas desactivar a "${cliente.razon_social}"? Podrás reactivarlo más adelante.`
            : ""
        }
        confirmLabel="Desactivar"
        destructive
        onConfirm={handleDeactivate}
      />
    </div>
  );
}
