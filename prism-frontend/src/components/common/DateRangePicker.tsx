/** PRISM FinOps — date range picker with presets. */

'use client';

import { format } from 'date-fns';
import { CalendarIcon } from 'lucide-react';
import { useState } from 'react';
import type { DateRange as DayPickerRange } from 'react-day-picker';

import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { formatDateForApi } from '@/lib/utils/dates';
import type { DateRange } from '@/types/api';

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
}

function toPickerRange(value: DateRange): DayPickerRange {
  return {
    from: new Date(value.start),
    to: new Date(value.end),
  };
}

function fromPickerRange(range: DayPickerRange | undefined): DateRange | null {
  if (!range?.from || !range.to) {
    return null;
  }
  return {
    start: formatDateForApi(range.from),
    end: formatDateForApi(range.to),
  };
}

function presetRange(days: number): DateRange {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - days + 1);
  return { start: formatDateForApi(start), end: formatDateForApi(end) };
}

/** Popover presets plus calendar for custom ranges. */
export function DateRangePicker({ value, onChange, className }: DateRangePickerProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<DayPickerRange>(toPickerRange(value));

  const label = `${format(new Date(value.start), 'MMM d')} – ${format(
    new Date(value.end),
    'MMM d, yyyy',
  )}`;

  const apply = (range: DateRange) => {
    onChange(range);
    setDraft(toPickerRange(range));
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger>
        <Button
          type="button"
          variant="outline"
          className={cn('justify-start font-normal', className)}
        >
          <CalendarIcon className="mr-2 size-4" />
          {label}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <div className="flex flex-wrap gap-1 border-b p-2">
          <Button type="button" size="sm" variant="ghost" onClick={() => apply(presetRange(7))}>
            Last 7 days
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => apply(presetRange(30))}>
            Last 30 days
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => apply(presetRange(90))}>
            Last 90 days
          </Button>
        </div>
        <Calendar
          mode="range"
          selected={draft}
          onSelect={(range) => {
            if (range) {
              setDraft(range);
              const next = fromPickerRange(range);
              if (next) {
                apply(next);
              }
            }
          }}
          numberOfMonths={2}
        />
      </PopoverContent>
    </Popover>
  );
}
