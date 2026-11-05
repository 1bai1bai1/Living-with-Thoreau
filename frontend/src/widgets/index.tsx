// The fixed library of components a scene can show (see backend/app/widget_specs.py).
// The server names a component and sends props it filled in itself, so the
// browser only ever renders components we wrote.

import type { Action, BlueprintProps, LedgerProps, WidgetEvent } from '../api';
import Blueprint from './Blueprint';
import Ledger from './Ledger';
import MaterialCard, { type MaterialCardProps } from './MaterialCard';
import TripPlanner, { type TripPlannerProps } from './TripPlanner';

type Ctx = { act: (a: Action) => void; locked: boolean };

const REGISTRY: Record<string, (props: unknown, ctx: Ctx) => JSX.Element> = {
  material_card: (p) => <MaterialCard props={p as MaterialCardProps} />,
  trip_planner: (p, ctx) => <TripPlanner props={p as TripPlannerProps} act={ctx.act} locked={ctx.locked} />,
  blueprint: (p) => <Blueprint props={p as BlueprintProps} />,
  ledger: (p) => <Ledger props={p as LedgerProps} />,
};

export function Widget({ widget, act, locked }: { widget: WidgetEvent } & Ctx) {
  // 'choices' aren't drawn here: they become chips by the text box (see Composer).
  const render = REGISTRY[widget.component];
  // An unknown component (an older frontend) shows nothing; the story still reads.
  return render ? render(widget.props, { act, locked }) : null;
}

export { Blueprint, Ledger };
