export interface CeldaCrear {
  codigo: string;
  tipo: string;
}
export type CeldaActualizar = Partial<CeldaCrear>;
export interface Celda extends CeldaCrear {
  id: number;
}
export interface OcupacionCelda extends Celda {
  ocupada: boolean;
  placa: string | null;
  entrada: string | null;
}
export interface CeldasPagina {
  items: Celda[];
  total: number;
  offset: number;
  limit: number;
}
