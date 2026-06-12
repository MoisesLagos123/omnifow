import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, RotateCcw, Users } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Table, type TableColumn } from "../../components/ui/Table";
import { SearchInput } from "../../components/ui/SearchInput";
import { Select } from "../../components/ui/Select";
import { Pagination } from "../../components/ui/Pagination";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState } from "../../components/ui/EmptyState";
import { useToast } from "../../components/ui/Toast";
import { RequirePermission } from "../../auth/RequirePermission";
import { usePermission, useAnyPermission } from "../../auth/usePermission";
import { clientesApi, type Cliente } from "../../api/clientes";
import { describeError } from "../../api/errorMessages";
import { formatCLP } from "../../lib/format";
import { formatearRut } from "../administracion/rut";
import { ROUTES } from "../../routePaths";
import styles from "./ClientesPages.module.css";

const LIMIT = 50;
type ActivoFiltro = "" | "true" | "false";

export function ClientesPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const canGestionar = usePermission("cliente.gestionar");
  const canCxC = useAnyPermission(["cxc.consultar", "cxc.gestionar"] as const);
  const [q, setQ] = useState("");
  const [activo, setActivo] = useState<ActivoFiltro>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{ items: Cliente[]; total: number } | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [reactivandoId, setReactivandoId] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    setLoading(true);
    setErrorMsg(null);
    clientesApi
      .listClientes(
        {
          q: q || undefined,
          activo: activo === "" ? undefined : activo === "true",
          limit: LIMIT,
          offset,
        },
        ctl.signal
      )
      .then((res) => setData({ items: res.items, total: res.total }))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setErrorMsg(describeError(err));
      })
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [q, activo, offset, reloadTick]);

  async function handleReactivar(
    c: Cliente,
    ev: MouseEvent<HTMLButtonElement>
  ) {
    ev.stopPropagation();
    setReactivandoId(c.id);
    try {
      await clientesApi.reactivarCliente(c.id);
      toast.success("Cliente reactivado", c.razon_social);
      setReloadTick((t) => t + 1);
    } catch (err) {
      toast.error("No se pudo reactivar", describeError(err));
    } finally {
      setReactivandoId(null);
    }
  }

  const columns = useMemo<TableColumn<Cliente>[]>(
    () => [
      {
        key: "rut",
        header: "RUT",
        width: "140px",
        cell: (c) => (
          <span
            style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}
          >
            {formatearRut(c.rut)}
          </span>
        ),
      },
      {
        key: "razon_social",
        header: "Razón social",
        cell: (c) => <strong>{c.razon_social}</strong>,
      },
      {
        key: "email",
        header: "Email",
        cell: (c) =>
          c.email ? (
            <span style={{ fontSize: "0.88rem" }}>{c.email}</span>
          ) : (
            <em className={styles.muted}>—</em>
          ),
      },
      {
        key: "telefono",
        header: "Teléfono",
        width: "130px",
        cell: (c) =>
          c.telefono ? (
            <span
              style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}
            >
              {c.telefono}
            </span>
          ) : (
            <em className={styles.muted}>—</em>
          ),
      },
      ...(canCxC
        ? ([
            {
              key: "saldo_cxc",
              header: "Saldo CxC",
              width: "120px",
              align: "right" as const,
              cell: (c: Cliente) =>
                (c.saldo_cxc_clp ?? 0) > 0 ? (
                  <Link
                    to={`${ROUTES.CXC}?cliente_id=${c.id}`}
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.85rem",
                      color: "var(--color-danger)",
                      fontWeight: 700,
                      textDecoration: "none",
                    }}
                    title="Ver cuentas por cobrar de este cliente"
                  >
                    {formatCLP(c.saldo_cxc_clp ?? 0)}
                  </Link>
                ) : (
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.85rem",
                      color: "var(--color-text-muted)",
                    }}
                  >
                    {formatCLP(0)}
                  </span>
                ),
            },
          ] as TableColumn<Cliente>[])
        : []),
      {
        key: "activo",
        header: "Estado",
        width: "100px",
        cell: (c) =>
          c.activo ? (
            <Badge variant="success">Activo</Badge>
          ) : (
            <Badge variant="neutral">Inactivo</Badge>
          ),
      },
      {
        key: "acciones",
        header: "",
        width: "130px",
        align: "right",
        cell: (c) =>
          !c.activo && canGestionar ? (
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<RotateCcw size={14} aria-hidden="true" />}
              loading={reactivandoId === c.id}
              onClick={(e) => handleReactivar(c, e)}
            >
              Reactivar
            </Button>
          ) : null,
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [reactivandoId, canGestionar, canCxC]
  );

  const isEmptyInitial =
    !loading && data?.items.length === 0 && !q && activo === "";

  return (
    <div className={styles.page}>
      <PageHeader
        title="Clientes"
        subtitle="Personas o empresas a las que se emiten documentos tributarios y se asocian ventas a crédito."
        actions={
          <RequirePermission code="cliente.gestionar">
            <Button
              leftIcon={<Plus size={16} aria-hidden="true" />}
              onClick={() => navigate(ROUTES.CLIENTE_NUEVO)}
            >
              Crear cliente
            </Button>
          </RequirePermission>
        }
      />

      <div className={styles.filters}>
        <div className={styles.searchSlot}>
          <SearchInput
            value={q}
            onChange={(v) => {
              setOffset(0);
              setQ(v);
            }}
            placeholder="Buscar por RUT o razón social..."
            label="Buscar clientes"
          />
        </div>
        <Select
          aria-label="Filtrar por estado"
          value={activo}
          onChange={(e) => {
            setOffset(0);
            setActivo(e.target.value as ActivoFiltro);
          }}
          options={[
            { value: "true", label: "Activos" },
            { value: "false", label: "Inactivos" },
          ]}
          emptyLabel="Todos"
        />
      </div>

      {errorMsg && (
        <div className={styles.errorWrap}>
          <ErrorAlert>{errorMsg}</ErrorAlert>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setReloadTick((t) => t + 1)}
          >
            Reintentar
          </Button>
        </div>
      )}

      <Table<Cliente>
        columns={columns}
        rows={data?.items}
        loading={loading}
        rowKey={(c) => c.id}
        onRowClick={(c) => navigate(ROUTES.CLIENTE_DETALLE(c.id))}
        emptyState={
          isEmptyInitial ? (
            <EmptyState
              icon={<Users size={28} />}
              title="Sin clientes aún"
              description="Crea el primer cliente para comenzar a emitir documentos tributarios."
              action={
                <RequirePermission code="cliente.gestionar">
                  <Button
                    size="sm"
                    leftIcon={<Plus size={14} aria-hidden="true" />}
                    onClick={() => navigate(ROUTES.CLIENTE_NUEVO)}
                  >
                    Crear el primer cliente
                  </Button>
                </RequirePermission>
              }
            />
          ) : q || activo !== "" ? (
            <EmptyState
              variant="inline"
              icon={<Users size={22} />}
              title="Sin resultados"
              description="No hay clientes que coincidan con los filtros aplicados."
            />
          ) : (
            "No hay clientes aún."
          )
        }
        caption="Listado de clientes"
      />

      <Pagination
        total={data?.total ?? 0}
        limit={LIMIT}
        offset={offset}
        onChange={setOffset}
      />
    </div>
  );
}
