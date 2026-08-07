"""Inference Scheduler"""
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from queue import PriorityQueue
import time


class TaskPriority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class InferenceTask:
    """Inference task"""
    id: str
    prompt: str
    max_tokens: int
    temperature: float
    top_p: float
    callback: Optional[Callable] = None
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = 0
    
    def __post_init__(self):
        self.created_at = time.time()
    
    def __lt__(self, other):
        return (self.priority.value, self.created_at) < (other.priority.value, other.created_at)


class InferenceScheduler:
    """Schedule and manage inference tasks"""
    
    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self.queue: PriorityQueue = PriorityQueue()
        self.active_tasks: Dict[str, InferenceTask] = {}
        self.running = False
        self._lock = asyncio.Lock()
    
    async def submit(self, task: InferenceTask) -> str:
        """Submit task to queue"""
        self.queue.put(task)
        return task.id
    
    async def start(self, engine):
        """Start scheduler loop"""
        self.running = True
        self.engine = engine
        
        while self.running:
            if not self.queue.empty() and len(self.active_tasks) < self.max_concurrent:
                task = self.queue.get()
                asyncio.create_task(self._process_task(task))
            
            await asyncio.sleep(0.01)
    
    async def stop(self):
        """Stop scheduler"""
        self.running = False
    
    async def _process_task(self, task: InferenceTask):
        """Process single task"""
        async with self._lock:
            self.active_tasks[task.id] = task
        
        try:
            result = await self.engine.generate(
                prompt=task.prompt,
                max_tokens=task.max_tokens,
                temperature=task.temperature,
                top_p=task.top_p
            )
            
            if task.callback:
                task.callback(result)
                
        finally:
            async with self._lock:
                del self.active_tasks[task.id]
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def get_active_count(self) -> int:
        """Get active task count"""
        return len(self.active_tasks)