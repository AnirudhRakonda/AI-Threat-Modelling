"""
Concurrent execution utilities for parallel LLM calls.
Enables faster processing by running independent tasks simultaneously.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def run_parallel_tasks(tasks: List[Tuple[Callable, tuple, str]]) -> Dict[str, Any]:
    """
    Execute multiple tasks in parallel using ThreadPoolExecutor.
    
    Args:
        tasks: List of (function, args_tuple, task_name) tuples
               Example: [(func1, (arg1, arg2), "task1_name"), ...]
    
    Returns:
        Dict mapping task names to results
        
    Example:
        tasks = [
            (vision_func, (img_bytes,), "vision"),
            (stride_func, (description,), "stride")
        ]
        results = run_parallel_tasks(tasks)
        # results["vision"] = vision output
        # results["stride"] = stride output
    """
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=min(len(tasks), 4)) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(task[0], *task[1]): task[2]
            for task in tasks
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_task):
            task_name = future_to_task[future]
            try:
                result = future.result()
                results[task_name] = result
                logger.info(f"Task '{task_name}' completed successfully")
            except Exception as e:
                logger.error(f"Task '{task_name}' failed: {str(e)}")
                results[task_name] = None
    
    return results


def run_sequential_with_fallback(task_func: Callable, args: tuple, 
                                  fallback_value: Any = None) -> Any:
    """
    Execute a task with fallback on failure.
    
    Args:
        task_func: Function to execute
        args: Arguments tuple
        fallback_value: Value to return if task fails
    
    Returns:
        Task result or fallback_value
    """
    try:
        return task_func(*args)
    except Exception as e:
        logger.warning(f"Task failed, using fallback: {str(e)}")
        return fallback_value
