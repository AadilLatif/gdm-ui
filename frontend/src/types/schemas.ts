// ===== Enums =====
export const ENUMS: Record<string, string[]> = {
  ConnectionType: ['STAR', 'DELTA', 'OPEN_DELTA', 'OPEN_STAR', 'ZIG_ZAG'],
  VoltageTypes: ['line-to-line', 'line-to-ground'],
  TransformerMounting: ['POLE_MOUNT', 'PAD_MOUNT', 'UNDERGROUND_VAULT'],
  LineType: ['OVERHEAD', 'UNDERGROUND'],
  WireInsulationType: ['AIR', 'PVC', 'XLPE', 'EPR', 'PE', 'TEFLON', 'SILICONE_RUBBER', 'PAPER', 'MICA'],
  Phase: ['A', 'B', 'C', 'N', 'S1', 'S2'],
}

// ===== Icons =====
export const ICONS: Record<string, string> = {
  BareConductorEquipment: 'pi pi-conductor',
  ConcentricCableEquipment: 'pi pi-cable',
  DistributionTransformerEquipment: 'pi pi-transformer',
  CapacitorEquipment: 'pi pi-capacitor',
  LoadEquipment: 'pi pi-load',
  SolarEquipment: 'pi pi-solar',
  BatteryEquipment: 'pi pi-battery',
  InverterEquipment: 'pi pi-inverter',
  VoltageSourceEquipment: 'pi pi-vsource',
  MatrixImpedanceBranchEquipment: 'pi pi-impedance',
  SequenceImpedanceBranchEquipment: 'pi pi-impedance',
  GeometryBranchEquipment: 'pi pi-geometry',
  MatrixImpedanceFuseEquipment: 'pi pi-fuse',
  MatrixImpedanceRecloserEquipment: 'pi pi-recloser',
  MatrixImpedanceSwitchEquipment: 'pi pi-switch',
  RecloserControllerEquipment: 'pi pi-controller',
  PhaseLoadEquipment: 'pi pi-load',
  PhaseCapacitorEquipment: 'pi pi-capacitor',
  PhaseVoltageSourceEquipment: 'pi pi-vsource',
  WindingEquipment: 'pi pi-winding',
}

export const COMPONENT_ICONS: Record<string, string> = {
  DistributionBus: 'pi pi-bus',
  DistributionLoad: 'pi pi-load',
  DistributionSolar: 'pi pi-solar',
  DistributionBattery: 'pi pi-battery',
  DistributionCapacitor: 'pi pi-capacitor',
  DistributionVoltageSource: 'pi pi-vsource',
  DistributionTransformer: 'pi pi-transformer',
  MatrixImpedanceBranch: 'pi pi-impedance',
  SequenceImpedanceBranch: 'pi pi-impedance',
  GeometryBranch: 'pi pi-geometry',
  MatrixImpedanceFuse: 'pi pi-fuse',
  MatrixImpedanceRecloser: 'pi pi-recloser',
  MatrixImpedanceSwitch: 'pi pi-switch',
}

// ===== Categories =====
export const CATEGORIES: Record<string, string[]> = {
  'Conductors & Cables': ['BareConductorEquipment', 'ConcentricCableEquipment'],
  'Transformers': ['DistributionTransformerEquipment', 'WindingEquipment'],
  'Loads': ['LoadEquipment', 'PhaseLoadEquipment'],
  'Capacitors': ['CapacitorEquipment', 'PhaseCapacitorEquipment'],
  'Generation': ['SolarEquipment', 'BatteryEquipment', 'InverterEquipment'],
  'Sources': ['VoltageSourceEquipment', 'PhaseVoltageSourceEquipment'],
  'Branches': ['MatrixImpedanceBranchEquipment', 'SequenceImpedanceBranchEquipment', 'GeometryBranchEquipment'],
  'Protection': ['MatrixImpedanceFuseEquipment', 'MatrixImpedanceRecloserEquipment', 'MatrixImpedanceSwitchEquipment', 'RecloserControllerEquipment'],
}

// ===== Schema Field Definition =====
export interface FieldDef {
  type: 'string' | 'quantity' | 'enum' | 'boolean' | 'integer' | 'float' | 'array_float' | 'array_json' | 'matrix' | 'nested_list' | 'phase_select' | 'equipment_ref' | 'winding_phases'
  description?: string
  unit?: string
  required?: boolean
  default?: unknown
  enum?: string
  schema?: string
  gt?: number
  ge?: number
  le?: number
  equipmentType?: string
}

export interface Schema {
  label: string
  busMode?: 'none' | 'single' | 'dual'
  fields: Record<string, FieldDef>
}

function qty(desc: string, unit: string, opts: Partial<FieldDef> = {}): FieldDef {
  return { type: 'quantity', description: desc, unit, ...opts }
}

export const SCHEMAS: Record<string, Schema> = {
  BareConductorEquipment: {
    label: 'Bare Conductor',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      conductor_diameter: qty('Diameter of the conductor', 'in', { gt: 0, required: true }),
      conductor_gmr: qty('Geometric mean radius of the conductor', 'ft', { gt: 0, required: true }),
      ampacity: qty('Ampacity of the conductor', 'A', { gt: 0, required: true }),
      ac_resistance: qty('AC resistance per unit length', 'ohm/mi', { gt: 0, required: true }),
      dc_resistance: qty('DC resistance per unit length', 'ohm/mi', { gt: 0, required: true }),
      emergency_ampacity: qty('Emergency ampacity', 'A', { gt: 0, required: true }),
    },
  },
  ConcentricCableEquipment: {
    label: 'Concentric Cable',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      strand_diameter: qty('Diameter of the cable strand', 'in', { gt: 0, required: true }),
      conductor_diameter: qty('Diameter of the conductor inside cable', 'in', { gt: 0, required: true }),
      cable_diameter: qty('Diameter of the cable', 'in', { gt: 0, required: true }),
      insulation_thickness: qty('Thickness of insulation', 'in', { gt: 0, required: true }),
      insulation_diameter: qty('Diameter of the insulation', 'in', { gt: 0, required: true }),
      ampacity: qty('Ampacity of the conductor', 'A', { gt: 0, required: true }),
      conductor_gmr: qty('Geometric mean radius of conductor', 'ft', { gt: 0, required: true }),
      strand_gmr: qty('Geometric mean radius of strand', 'ft', { gt: 0, required: true }),
      phase_ac_resistance: qty('Per unit length conductor AC resistance', 'ohm/mi', { gt: 0, required: true }),
      strand_ac_resistance: qty('Per unit length strand AC resistance', 'ohm/mi', { gt: 0, required: true }),
      num_neutral_strands: { type: 'integer', description: 'Number of neutral strands', gt: 0, required: true },
      rated_voltage: qty('Rated voltage', 'kV', { gt: 0, required: true }),
      insulation: { type: 'enum', enum: 'WireInsulationType', description: 'Wire insulation type', default: 'PE' },
    },
  },
  WindingEquipment: {
    label: 'Winding',
    fields: {
      name: { type: 'string', description: 'Winding name', default: '' },
      resistance: { type: 'float', description: 'Percentage resistance', ge: 0, le: 100, required: true },
      is_grounded: { type: 'boolean', description: 'Is this winding grounded?', required: true },
      rated_voltage: qty('Rated voltage', 'kV', { gt: 0, required: true }),
      voltage_type: { type: 'enum', enum: 'VoltageTypes', description: 'Voltage type', required: true },
      rated_power: qty('Rated power', 'kVA', { gt: 0, required: true }),
      num_phases: { type: 'integer', description: 'Number of phases', ge: 1, le: 3, required: true },
      connection_type: { type: 'enum', enum: 'ConnectionType', description: 'Connection type', required: true },
      tap_positions: { type: 'array_float', description: 'Tap positions per phase', required: true },
      total_taps: { type: 'integer', description: 'Total number of taps', default: 32 },
      min_tap_pu: { type: 'float', description: 'Min tap in pu', default: 0.9, ge: 0, le: 1 },
      max_tap_pu: { type: 'float', description: 'Max tap in pu', default: 1.1, ge: 1 },
    },
  },
  DistributionTransformerEquipment: {
    label: 'Distribution Transformer',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      mounting: { type: 'enum', enum: 'TransformerMounting', description: 'Mounting type', default: 'POLE_MOUNT' },
      pct_no_load_loss: { type: 'float', description: '% no load losses', ge: 0, le: 100, required: true },
      pct_full_load_loss: { type: 'float', description: '% full load losses', ge: 0, le: 100, required: true },
      is_center_tapped: { type: 'boolean', description: 'Is center tapped?', required: true },
      windings: { type: 'nested_list', schema: 'WindingEquipment', description: 'Transformer windings', required: true },
      coupling_sequences: { type: 'array_json', description: 'Coupling sequences', required: true },
      winding_reactances: { type: 'array_float', description: 'Winding reactances', required: true },
    },
  },
  PhaseCapacitorEquipment: {
    label: 'Phase Capacitor',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      resistance: qty('Resistance', 'ohm', { ge: 0, default: 0 }),
      reactance: qty('Reactance', 'ohm', { ge: 0, default: 0 }),
      rated_reactive_power: qty('Rated reactive power', 'kvar', { gt: 0, required: true }),
      num_banks_on: { type: 'integer', description: 'Number of banks currently on', ge: 0, required: true },
      num_banks: { type: 'integer', description: 'Number of banks total', default: 1, gt: 0 },
    },
  },
  CapacitorEquipment: {
    label: 'Capacitor',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      connection_type: { type: 'enum', enum: 'ConnectionType', description: 'Connection type', default: 'STAR' },
      rated_voltage: qty('Rated voltage', 'kV', { gt: 0, required: true }),
      voltage_type: { type: 'enum', enum: 'VoltageTypes', description: 'Voltage type', required: true },
      phase_capacitors: { type: 'nested_list', schema: 'PhaseCapacitorEquipment', description: 'Phase capacitors', required: true },
    },
  },
  PhaseLoadEquipment: {
    label: 'Phase Load',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      real_power: qty('Base real power', 'kW', { default: 0 }),
      reactive_power: qty('Base reactive power', 'kvar', { default: 0 }),
      z_real: { type: 'float', description: 'Constant impedance ZIP real', required: true },
      z_imag: { type: 'float', description: 'Constant impedance ZIP imag', required: true },
      i_real: { type: 'float', description: 'Constant current ZIP real', required: true },
      i_imag: { type: 'float', description: 'Constant current ZIP imag', required: true },
      p_real: { type: 'float', description: 'Constant power ZIP real', required: true },
      p_imag: { type: 'float', description: 'Constant power ZIP imag', required: true },
      num_customers: { type: 'integer', description: 'Number of customers', gt: 0 },
    },
  },
  LoadEquipment: {
    label: 'Load',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      connection_type: { type: 'enum', enum: 'ConnectionType', description: 'Connection type', default: 'STAR' },
      phase_loads: { type: 'nested_list', schema: 'PhaseLoadEquipment', description: 'Phase loads', required: true },
    },
  },
  SolarEquipment: {
    label: 'Solar',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      rated_power: qty('Maximum power at 1.0 kW/m²', 'kW', { gt: 0, required: true }),
      resistance: { type: 'float', description: '% internal resistance', ge: 0, le: 100, required: true },
      reactance: { type: 'float', description: '% internal reactance', ge: 0, le: 100, required: true },
      rated_voltage: qty('Rated voltage', 'kV', { gt: 0, required: true }),
      voltage_type: { type: 'enum', enum: 'VoltageTypes', description: 'Voltage type', required: true },
    },
  },
  BatteryEquipment: {
    label: 'Battery',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      rated_energy: qty('Rated energy capacity (DC)', 'kWh', { required: true }),
      rated_power: qty('Rated power', 'kW', { ge: 0, required: true }),
      charging_efficiency: { type: 'float', description: 'Charging efficiency (%)', ge: 0, le: 100, required: true },
      discharging_efficiency: { type: 'float', description: 'Discharging efficiency (%)', ge: 0, le: 100, required: true },
      idling_efficiency: { type: 'float', description: 'Idling efficiency (%)', ge: 0, le: 100, required: true },
      rated_voltage: qty('Rated voltage', 'kV', { ge: 0, required: true }),
      voltage_type: { type: 'enum', enum: 'VoltageTypes', description: 'Voltage type', required: true },
    },
  },
  InverterEquipment: {
    label: 'Inverter',
    fields: {
      name: { type: 'string', description: 'Equipment name', default: '' },
      rated_apparent_power: qty('Apparent power rating', 'kVA', { gt: 0, required: true }),
      rise_limit: qty('Rise in power output per unit time', 'kW/s'),
      fall_limit: qty('Fall in power output per unit time', 'kW/s'),
      cutout_percent: { type: 'float', description: 'Cutout percent', ge: 0, le: 100, required: true },
      cutin_percent: { type: 'float', description: 'Cutin percent', ge: 0, le: 100, required: true },
      dc_to_ac_efficiency: { type: 'float', description: 'DC to AC efficiency (%)', ge: 0, le: 100, required: true },
    },
  },
  PhaseVoltageSourceEquipment: {
    label: 'Phase Voltage Source',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      r0: qty('Zero sequence resistance', 'ohm', { required: true }),
      r1: qty('Positive sequence resistance', 'ohm', { required: true }),
      x0: qty('Zero sequence reactance', 'ohm', { required: true }),
      x1: qty('Positive sequence reactance', 'ohm', { required: true }),
      voltage: qty('Voltage', 'kV', { gt: 0, required: true }),
      voltage_type: { type: 'enum', enum: 'VoltageTypes', description: 'Voltage type', default: 'line-to-line' },
      angle: qty('Voltage angle', 'deg', { required: true }),
    },
  },
  VoltageSourceEquipment: {
    label: 'Voltage Source',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      sources: { type: 'nested_list', schema: 'PhaseVoltageSourceEquipment', description: 'Phase voltage sources', required: true },
    },
  },
  MatrixImpedanceBranchEquipment: {
    label: 'Matrix Impedance Branch',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      construction: { type: 'enum', enum: 'LineType', description: 'Construction type', default: 'OVERHEAD' },
      r_matrix: { type: 'matrix', description: 'Resistance matrix (ohm/mi)', unit: 'ohm/mi', required: true },
      x_matrix: { type: 'matrix', description: 'Reactance matrix (ohm/mi)', unit: 'ohm/mi', required: true },
      c_matrix: { type: 'matrix', description: 'Capacitance matrix (nF/mi)', unit: 'nF/mi', required: true },
      ampacity: qty('Ampacity', 'A', { gt: 0, required: true }),
    },
  },
  SequenceImpedanceBranchEquipment: {
    label: 'Sequence Impedance Branch',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      pos_seq_resistance: qty('Positive sequence resistance', 'ohm/mi', { required: true }),
      zero_seq_resistance: qty('Zero sequence resistance', 'ohm/mi', { required: true }),
      pos_seq_reactance: qty('Positive sequence reactance', 'ohm/mi', { required: true }),
      zero_seq_reactance: qty('Zero sequence reactance', 'ohm/mi', { required: true }),
      pos_seq_capacitance: qty('Positive sequence capacitance', 'nF/mi', { required: true }),
      zero_seq_capacitance: qty('Zero sequence capacitance', 'nF/mi', { required: true }),
      ampacity: qty('Ampacity', 'A', { gt: 0, required: true }),
    },
  },
  GeometryBranchEquipment: {
    label: 'Geometry Branch',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      conductors: { type: 'nested_list', schema: 'BareConductorEquipment', description: 'Conductors', required: true },
      horizontal_positions: { type: 'array_float', description: 'Horizontal positions (m)', unit: 'm', required: true },
      vertical_positions: { type: 'array_float', description: 'Vertical positions (m)', unit: 'm', required: true },
      insulation: { type: 'enum', enum: 'WireInsulationType', description: 'Wire insulation type', default: 'AIR' },
    },
  },
  MatrixImpedanceFuseEquipment: {
    label: 'Matrix Impedance Fuse',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      construction: { type: 'enum', enum: 'LineType', description: 'Construction type', default: 'OVERHEAD' },
      r_matrix: { type: 'matrix', description: 'Resistance matrix (ohm/mi)', unit: 'ohm/mi', required: true },
      x_matrix: { type: 'matrix', description: 'Reactance matrix (ohm/mi)', unit: 'ohm/mi', required: true },
      c_matrix: { type: 'matrix', description: 'Capacitance matrix (nF/mi)', unit: 'nF/mi', required: true },
      ampacity: qty('Ampacity', 'A', { gt: 0, required: true }),
    },
  },
  MatrixImpedanceRecloserEquipment: {
    label: 'Matrix Impedance Recloser',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      construction: { type: 'enum', enum: 'LineType', description: 'Construction type', default: 'OVERHEAD' },
      r_matrix: { type: 'matrix', description: 'Resistance matrix (ohm/mi)', unit: 'ohm/mi', required: true },
      x_matrix: { type: 'matrix', description: 'Reactance matrix (ohm/mi)', unit: 'ohm/mi', required: true },
      c_matrix: { type: 'matrix', description: 'Capacitance matrix (nF/mi)', unit: 'nF/mi', required: true },
      ampacity: qty('Ampacity', 'A', { gt: 0, required: true }),
    },
  },
  MatrixImpedanceSwitchEquipment: {
    label: 'Matrix Impedance Switch',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
      construction: { type: 'enum', enum: 'LineType', description: 'Construction type', default: 'OVERHEAD' },
      r_matrix: { type: 'matrix', description: 'Resistance matrix (ohm/mi)', unit: 'ohm/mi', required: true },
      x_matrix: { type: 'matrix', description: 'Reactance matrix (ohm/mi)', unit: 'ohm/mi', required: true },
      c_matrix: { type: 'matrix', description: 'Capacitance matrix (nF/mi)', unit: 'nF/mi', required: true },
      ampacity: qty('Ampacity', 'A', { gt: 0, required: true }),
    },
  },
  RecloserControllerEquipment: {
    label: 'Recloser Controller',
    fields: {
      name: { type: 'string', description: 'Equipment name', required: true },
    },
  },
}

// ===== Component Schemas (for Network page distribution components) =====
export const COMPONENT_SCHEMAS: Record<string, Schema> = {
  DistributionBus: {
    label: 'Distribution Bus',
    busMode: 'none',
    fields: {
      name: { type: 'string', description: 'Bus name', required: true },
      voltage_type: { type: 'enum', enum: 'VoltageTypes', description: 'Voltage type', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      rated_voltage: qty('Rated voltage', 'V', { gt: 0, required: true }),
    },
  },
  DistributionLoad: {
    label: 'Load',
    busMode: 'single',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      equipment: { type: 'equipment_ref', equipmentType: 'LoadEquipment', description: 'Load equipment' },
    },
  },
  DistributionSolar: {
    label: 'Solar PV',
    busMode: 'single',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      irradiance: qty('Irradiance', 'kW/m²', { ge: 0, required: true }),
      active_power: qty('Active power output', 'kW', { ge: 0, required: true }),
      reactive_power: qty('Reactive power output', 'kvar', { required: true }),
      equipment: { type: 'equipment_ref', equipmentType: 'SolarEquipment', description: 'Solar equipment' },
      inverter: { type: 'equipment_ref', equipmentType: 'InverterEquipment', description: 'Inverter equipment' },
    },
  },
  DistributionBattery: {
    label: 'Battery',
    busMode: 'single',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      active_power: qty('Active power output', 'kW', { required: true }),
      reactive_power: qty('Reactive power output', 'kvar', { required: true }),
      equipment: { type: 'equipment_ref', equipmentType: 'BatteryEquipment', description: 'Battery equipment' },
      inverter: { type: 'equipment_ref', equipmentType: 'InverterEquipment', description: 'Inverter equipment' },
    },
  },
  DistributionCapacitor: {
    label: 'Capacitor',
    busMode: 'single',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      equipment: { type: 'equipment_ref', equipmentType: 'CapacitorEquipment', description: 'Capacitor equipment' },
    },
  },
  DistributionVoltageSource: {
    label: 'Voltage Source',
    busMode: 'single',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      equipment: { type: 'equipment_ref', equipmentType: 'VoltageSourceEquipment', description: 'Voltage source equipment' },
    },
  },
  DistributionTransformer: {
    label: 'Transformer',
    busMode: 'dual',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      winding_phases: { type: 'winding_phases', description: 'Phases per winding', required: true },
      equipment: { type: 'equipment_ref', equipmentType: 'DistributionTransformerEquipment', description: 'Transformer equipment' },
    },
  },
  MatrixImpedanceBranch: {
    label: 'Impedance Branch',
    busMode: 'dual',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      length: qty('Length', 'm', { gt: 0, required: true }),
      equipment: { type: 'equipment_ref', equipmentType: 'MatrixImpedanceBranchEquipment', description: 'Branch equipment' },
    },
  },
  SequenceImpedanceBranch: {
    label: 'Sequence Branch',
    busMode: 'dual',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      length: qty('Length', 'm', { gt: 0, required: true }),
      equipment: { type: 'equipment_ref', equipmentType: 'SequenceImpedanceBranchEquipment', description: 'Branch equipment' },
    },
  },
  GeometryBranch: {
    label: 'Geometry Branch',
    busMode: 'dual',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      length: qty('Length', 'm', { gt: 0, required: true }),
      equipment: { type: 'equipment_ref', equipmentType: 'GeometryBranchEquipment', description: 'Branch equipment' },
    },
  },
  MatrixImpedanceFuse: {
    label: 'Fuse',
    busMode: 'dual',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      length: qty('Length', 'm', { gt: 0, required: true }),
      is_closed: { type: 'array_float', description: 'Status per phase (closed?)', required: true },
      equipment: { type: 'equipment_ref', equipmentType: 'MatrixImpedanceFuseEquipment', description: 'Fuse equipment' },
    },
  },
  MatrixImpedanceRecloser: {
    label: 'Recloser',
    busMode: 'dual',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      length: qty('Length', 'm', { gt: 0, required: true }),
      is_closed: { type: 'array_float', description: 'Status per phase (closed?)', required: true },
      equipment: { type: 'equipment_ref', equipmentType: 'MatrixImpedanceRecloserEquipment', description: 'Recloser equipment' },
    },
  },
  MatrixImpedanceSwitch: {
    label: 'Switch',
    busMode: 'dual',
    fields: {
      name: { type: 'string', description: 'Component name', required: true },
      phases: { type: 'phase_select', description: 'Phases', required: true },
      length: qty('Length', 'm', { gt: 0, required: true }),
      is_closed: { type: 'array_float', description: 'Status per phase (closed?)', required: true },
      equipment: { type: 'equipment_ref', equipmentType: 'MatrixImpedanceSwitchEquipment', description: 'Switch equipment' },
    },
  },
}
