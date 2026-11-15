export interface Tiquete {
  numero: string;
  estancia_id: number;
  placa: string;
  tipo_vehiculo: string;
  entrada: string;
  celda_codigo: string;
  puerta: 'Entrada';
  operador_id: number;
  operador_nombre: string;
  reconstruido: boolean;
}

export interface Movimiento {
  estancia_id: number;
  tiquete_numero: string;
  placa: string;
  tipo_vehiculo: string;
  movimiento: 'ENTRADA' | 'SALIDA';
  fecha: string;
  celda_id: number;
  celda_codigo: string;
  puerta: string;
  operador_id: number;
  operador_nombre: string;
}

export interface FiltrosMovimientos {
  placa: string;
  desde: string;
  hasta: string;
  celda_id: number | null;
  operador_id: number | null;
  movimiento: string;
}

export interface MovimientosPagina {
  items: Movimiento[];
  total: number;
  entradas: number;
  salidas: number;
  offset: number;
  limit: number;
}
