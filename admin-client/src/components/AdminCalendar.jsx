import React, { useState } from 'react';
import { 
  format, 
  startOfWeek, 
  endOfWeek, 
  eachDayOfInterval, 
  startOfMonth, 
  endOfMonth, 
  isSameMonth, 
  isSameDay, 
  addMonths, 
  subMonths,
  parseISO,
  isToday
} from 'date-fns';
import { ChevronLeft, ChevronRight, Video, Calendar as CalendarIcon, Clock, X } from 'lucide-react';

export default function AdminCalendar({ scheduledRequests = [] }) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedRequest, setSelectedRequest] = useState(null);

  const nextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const prevMonth = () => setCurrentDate(subMonths(currentDate, 1));
  const goToToday = () => setCurrentDate(new Date());

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(monthStart);
  const startDate = startOfWeek(monthStart);
  const endDate = endOfWeek(monthEnd);

  const days = eachDayOfInterval({ start: startDate, end: endDate });

  // Group events by date string (YYYY-MM-DD)
  const eventsByDate = scheduledRequests.reduce((acc, req) => {
    if (req.scheduled_date) {
      if (!acc[req.scheduled_date]) {
        acc[req.scheduled_date] = [];
      }
      acc[req.scheduled_date].push(req);
    }
    return acc;
  }, {});

  return (
    <div className="bg-card border border-border/50 rounded-xl overflow-hidden flex flex-col">
      {/* Calendar Header */}
      <div className="p-6 border-b border-border/50 flex items-center justify-between bg-muted/20">
        <div className="flex items-center gap-3">
          <CalendarIcon className="text-primary w-6 h-6" />
          <h2 className="text-2xl font-bold">{format(currentDate, 'MMMM yyyy')}</h2>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={goToToday}
            className="px-4 py-2 text-sm font-semibold border border-border rounded-lg hover:bg-muted mr-2"
          >
            Today
          </button>
          <button 
            onClick={prevMonth}
            className="p-2 border border-border rounded-lg hover:bg-muted"
          >
            <ChevronLeft size={20} />
          </button>
          <button 
            onClick={nextMonth}
            className="p-2 border border-border rounded-lg hover:bg-muted"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      {/* Days of week header */}
      <div className="grid grid-cols-7 border-b border-border/50 bg-muted/30">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
          <div key={day} className="py-3 text-center text-xs font-semibold uppercase text-muted-foreground">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 auto-rows-fr">
        {days.map((day, idx) => {
          const dateKey = format(day, 'yyyy-MM-dd');
          const dayEvents = eventsByDate[dateKey] || [];
          const isCurrentMonth = isSameMonth(day, monthStart);
          const isCurrentDay = isToday(day);

          return (
            <div 
              key={day.toString()} 
              className={`min-h-[120px] p-2 border-b border-r border-border/50 transition-colors ${
                !isCurrentMonth ? 'bg-muted/10 opacity-50' : 'bg-card'
              } hover:bg-muted/30`}
            >
              <div className="flex justify-between items-start mb-2">
                <span className={`text-sm font-semibold w-7 h-7 flex items-center justify-center rounded-full ${
                  isCurrentDay ? 'bg-primary text-primary-foreground' : 'text-foreground'
                }`}>
                  {format(day, 'd')}
                </span>
                {dayEvents.length > 0 && (
                  <span className="text-[10px] font-bold bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                    {dayEvents.length}
                  </span>
                )}
              </div>
              
              <div className="space-y-1">
                {dayEvents.map(event => (
                  <button
                    key={event.id}
                    onClick={() => setSelectedRequest(event)}
                    className="w-full text-left p-1.5 text-xs rounded border border-primary/20 bg-primary/5 hover:bg-primary/10 transition-colors truncate flex items-center gap-1"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                    <span className="font-semibold text-primary truncate">{event.scheduled_time}</span>
                    <span className="truncate ml-1 text-muted-foreground">{event.name}</span>
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Event Details Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="bg-card border border-border/50 rounded-xl w-full max-w-md shadow-2xl relative overflow-hidden">
            <div className="bg-primary/10 p-6 flex justify-between items-start">
              <div>
                <h3 className="text-xl font-bold text-foreground mb-1">Meeting Details</h3>
                <p className="text-sm text-primary font-semibold flex items-center gap-1">
                  <CalendarIcon size={14} /> 
                  {format(parseISO(selectedRequest.scheduled_date), 'EEEE, MMMM d, yyyy')}
                </p>
              </div>
              <button 
                onClick={() => setSelectedRequest(null)}
                className="text-muted-foreground hover:text-foreground bg-card rounded-full p-1"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-border/50 pb-4">
                <div>
                  <p className="text-sm text-muted-foreground">Client Name</p>
                  <p className="font-semibold">{selectedRequest.name}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">Time</p>
                  <p className="font-semibold flex items-center gap-1 justify-end">
                    <Clock size={14} className="text-muted-foreground" />
                    {selectedRequest.scheduled_time}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-sm text-muted-foreground mb-1">Email</p>
                <a href={`mailto:${selectedRequest.email}`} className="text-primary hover:underline text-sm font-medium">
                  {selectedRequest.email}
                </a>
              </div>
              
              {selectedRequest.company && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Company</p>
                  <p className="text-sm font-medium">{selectedRequest.company}</p>
                </div>
              )}

              <div className="pt-4 mt-2 border-t border-border/50">
                <a 
                  href={selectedRequest.meeting_link} 
                  target="_blank" 
                  rel="noreferrer"
                  className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground font-bold py-3 rounded-lg transition-colors shadow-lg"
                >
                  <Video size={18} />
                  Join Google Meet
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
