# FLO-2D Model Data Extraction Performance Optimization TODO

## Overview
This document outlines a comprehensive plan to optimize the `model_data_extraction.py` module to achieve **2-8x performance improvements** by expanding parallel processing capabilities and consolidating sequential file operations.

## Current State Analysis

### Performance Bottlenecks Identified
- **16 files** currently processed in parallel via `FILE_EXTRACTORS`
- **12-15 additional files** processed sequentially in `main.py`
- Estimated **3-8x potential speedup** available through parallelization
- Memory usage could increase 3-5x but manageable with existing Dask optimizations

### Sequential Operations in main.py (Lines 217-517)
```
SUPER.OUT → EVACUATEDFP.OUT → TIME.OUT → INFLOW.DAT → 
OUTFLOW.DAT + OUTNQ.OUT → HYCROSS.OUT → HYSTRUC.DAT + HYDROSTRUCT.OUT → 
SWMM.inp → SWMMQIN.OUT → SWMMFLORT.DAT → Channel Data
```

## Implementation Plan

### Phase 1: Low-Risk Immediate Wins (Priority: HIGH)
**Estimated Speedup: 2-3x for extraction phase**
**Risk Level: LOW**
**Implementation Time: 1-2 days**

#### Task 1.1: Expand FILE_EXTRACTORS Dictionary
**File: `/workspace/core/model_data_extraction.py`**

Add the following immediately parallelizable files to `FILE_EXTRACTORS`:

```python
FILE_EXTRACTORS = {
    # ... existing entries ...
    'EVACUATEDFP.OUT': extract_evacuatedfp_out,
    'TIME.OUT': extract_time_out,
    'INFLOW.DAT': extract_inflow_dat,
    'SWMMFLORT.DAT': extract_swmmflort_dat,
}
```

**Required Imports to Add:**
```python
from extraction.out.evacuatedfp_out_extraction import extract_evacuatedfp_out
from extraction.out.time_out_extraction import extract_time_out
from extraction.dat.inflow_dat_extraction import extract_inflow_dat
from extraction.dat.swmmflort_dat_extraction import extract_swmmflort_dat
```

#### Task 1.2: Update Merge Logic
**File: `/workspace/core/model_data_extraction.py`**

Add merge handling for new files in `extract_model_data_to_df()`:

```python
# After line 120, add conditional merges for new files
if 'EVACUATEDFP.OUT' in data_frames:
    logger.info("Merging EVACUATEDFP.OUT data...")
    main_df = pd.merge(main_df, data_frames['EVACUATEDFP.OUT'], on=GRID_ID, how='left')

if 'TIME.OUT' in data_frames:
    logger.info("Merging TIME.OUT data...")
    main_df = pd.merge(main_df, data_frames['TIME.OUT'], on=GRID_ID, how='left')

# INFLOW.DAT and SWMMFLORT.DAT may need special handling due to different data structures
```

#### Task 1.3: Remove Redundant Sequential Calls
**File: `/workspace/main.py`**

Remove or comment out the sequential extraction calls for files now handled in parallel:
- Lines 217-218: `extract_super_out()` - **ALREADY HANDLED**
- Lines 261-262: `extract_evacuatedfp_out()` - **REMOVE**
- Lines 305-306: `extract_time_out()` - **REMOVE**
- Lines 502: `extract_swmmflort_dat()` - **REMOVE**

**Note:** Keep the post-processing and shapefile generation logic, just remove the extraction calls.

### Phase 2: Medium-Risk Coordinated Operations (Priority: MEDIUM)
**Estimated Additional Speedup: 1.5-2x**
**Risk Level: MEDIUM**
**Implementation Time: 2-3 days**

#### Task 2.1: Parallel Multi-File Processors
**File: `/workspace/core/model_data_extraction.py`**

Create specialized parallel processors for related file groups:

```python
COORDINATED_EXTRACTORS = {
    'OUTFLOW_GROUP': {
        'files': ['OUTFLOW.DAT', 'OUTNQ.OUT'],
        'processor': extract_coordinated_outflow_data,
        'dependencies': None
    },
    'HYSTRUC_GROUP': {
        'files': ['HYSTRUC.DAT', 'HYDROSTRUCT.OUT'],
        'processor': extract_coordinated_hystruc_data,
        'dependencies': None
    },
    'SWMM_GROUP': {
        'files': ['SWMM.inp', 'SWMMQIN.OUT'],
        'processor': extract_coordinated_swmm_data,
        'dependencies': None
    }
}
```

#### Task 2.2: Create Coordinated Extraction Functions
**New Files to Create:**
- `/workspace/extraction/coordinated/outflow_coordinated_extraction.py`
- `/workspace/extraction/coordinated/hystruc_coordinated_extraction.py`
- `/workspace/extraction/coordinated/swmm_coordinated_extraction.py`

Each function should:
1. Run related extractions in parallel using ThreadPoolExecutor
2. Return a dictionary with separate DataFrames for each file type
3. Handle error cases gracefully

#### Task 2.3: Update Main Processing Logic
**File: `/workspace/core/model_data_extraction.py`**

Add coordinated processing after main parallel extraction:

```python
# After line 92, add coordinated processing
coordinated_data = {}
for group_name, config in COORDINATED_EXTRACTORS.items():
    try:
        result = config['processor'](file_path)
        if result:
            coordinated_data.update(result)
            logger.info(f"Processed {group_name}: {len(result)} datasets")
    except Exception as e:
        logger.error(f"Error processing {group_name}: {e}")

# Merge coordinated data with main DataFrame
data_frames.update(coordinated_data)
```

### Phase 3: Complex Multi-File Operations (Priority: LOW)
**Estimated Additional Speedup: 1.2-1.5x**
**Risk Level: HIGH**
**Implementation Time: 3-5 days**

#### Task 3.1: Channel Data Optimization
**File: `/workspace/extraction/out/channel_extraction.py`**

Optimize the existing `extract_channel_data()` to use internal parallelization:

```python
def extract_channel_data_parallel(path):
    """Parallel version of channel data extraction."""
    with ThreadPoolExecutor(max_workers=min(5, multiprocessing.cpu_count())) as executor:
        futures = {
            executor.submit(extract_xsec_dat, path): 'XSEC',
            executor.submit(extract_chanmax_out, path): 'CHANMAX',
            executor.submit(extract_chan_dat, path): 'CHAN',
        }
        # ... rest of implementation
```

#### Task 3.2: FPXSEC/HYCROSS Optimization
**File: `/workspace/extraction/out/hycross_out_extraction.py`**

Add parallel processing capabilities to cross-section analysis.

### Phase 4: Infrastructure Improvements (Priority: MEDIUM)
**Implementation Time: 2-3 days**

#### Task 4.1: Enhanced Error Handling
**File: `/workspace/core/model_data_extraction.py`**

Improve error handling for parallel operations:

```python
def extract_with_retry(func, file_path, max_retries=2):
    """Extract data with retry logic for failed operations."""
    for attempt in range(max_retries + 1):
        try:
            return func(file_path)
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Final attempt failed for {func.__name__}: {e}")
                return None
            logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
            time.sleep(1)
```

#### Task 4.2: Memory Usage Monitoring
**File: `/workspace/core/model_data_extraction.py`**

Add memory monitoring to prevent out-of-memory issues:

```python
def monitor_memory_usage():
    """Monitor memory usage during parallel processing."""
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > 85:
        logger.warning(f"High memory usage detected: {memory_percent}%")
        return False
    return True
```

#### Task 4.3: Progress Reporting Enhancement
**File: `/workspace/core/model_data_extraction.py`**

Enhance progress reporting for GUI integration:

```python
def extract_model_data_to_df_with_progress(file_path: str, progress_callback=None) -> pd.DataFrame:
    """Enhanced version with progress reporting."""
    total_operations = len(FILE_EXTRACTORS) + len(COORDINATED_EXTRACTORS)
    completed_operations = 0
    
    def update_progress():
        nonlocal completed_operations
        completed_operations += 1
        if progress_callback:
            progress_callback(completed_operations / total_operations * 100)
```

### Phase 5: Testing and Validation (Priority: HIGH)
**Implementation Time: 2-3 days**

#### Task 5.1: Performance Benchmarking
Create comprehensive benchmarks to measure:
- **Before/after processing times** for different dataset sizes
- **Memory usage patterns** during parallel vs sequential processing
- **I/O throughput** improvements
- **CPU utilization** during processing

**New File:** `/workspace/tests/performance/benchmark_extraction.py`

#### Task 5.2: Data Integrity Testing
Ensure parallel processing produces identical results:
- **Compare outputs** between sequential and parallel processing
- **Validate DataFrame merges** produce consistent results
- **Test error handling** for missing files and corrupted data

**New File:** `/workspace/tests/integration/test_parallel_extraction.py`

#### Task 5.3: Memory Usage Testing
Test memory usage under various conditions:
- **Small datasets** (< 100MB)
- **Medium datasets** (100MB - 1GB)
- **Large datasets** (> 1GB)
- **Missing file scenarios**

#### Task 5.4: Regression Testing
Ensure all existing functionality remains intact:
- **Run full test suite** after each phase
- **Validate output file formats** match expectations
- **Test GUI integration** with new progress reporting

## Implementation Timeline

### Week 1: Phase 1 (Immediate Wins)
- **Day 1-2:** Implement basic FILE_EXTRACTORS expansion
- **Day 3:** Update merge logic and remove redundant calls
- **Day 4-5:** Testing and validation

### Week 2: Phase 2 (Coordinated Operations)
- **Day 1-2:** Create coordinated extraction functions
- **Day 3:** Implement coordinated processing logic
- **Day 4-5:** Testing and integration

### Week 3: Phase 4 & 5 (Infrastructure & Testing)
- **Day 1-2:** Implement enhanced error handling and monitoring
- **Day 3-5:** Comprehensive testing and benchmarking

### Week 4: Phase 3 (Complex Operations) - Optional
- **Day 1-3:** Channel data and FPXSEC optimizations
- **Day 4-5:** Final testing and documentation

## Success Metrics

### Performance Targets
- **Minimum 2x speedup** for data extraction phase (Phase 1)
- **Target 3-5x speedup** for full implementation (Phases 1-2)
- **Stretch goal 5-8x speedup** for optimal scenarios (All phases)

### Quality Targets
- **Zero regression** in output data quality
- **100% test coverage** for new parallel processing code
- **Maintained memory efficiency** (< 2x peak memory increase)

## Risk Mitigation

### Technical Risks
1. **Memory exhaustion** on large datasets
   - **Mitigation:** Implement memory monitoring and adaptive chunking
2. **Data race conditions** in parallel processing
   - **Mitigation:** Use immutable data structures and proper thread safety
3. **I/O contention** on slow storage
   - **Mitigation:** Adaptive worker count based on storage type

### Implementation Risks
1. **Breaking existing functionality**
   - **Mitigation:** Comprehensive regression testing
2. **Integration issues** with GUI
   - **Mitigation:** Maintain backward compatibility with progress callbacks
3. **Complex debugging** of parallel operations
   - **Mitigation:** Enhanced logging and error tracking

## Future Enhancements (Beyond Current Scope)

### Advanced Parallelization
- **Async I/O** for even better performance
- **GPU acceleration** for large data processing
- **Distributed processing** for massive datasets

### Smart Caching
- **File modification detection** to skip unchanged files
- **Partial extraction** for incremental updates
- **Memory-mapped files** for large datasets

### Dynamic Optimization
- **Storage type detection** for optimal worker count
- **Adaptive chunk sizing** based on available memory
- **Performance profiling** for continuous optimization

---

## Notes for Implementation

### Code Style Consistency
- Follow existing coding patterns in the codebase
- Use existing logging and error handling patterns
- Maintain consistency with current column naming conventions

### Documentation Requirements
- Update docstrings for all modified functions
- Add inline comments for complex parallel processing logic
- Update user documentation if interface changes

### Backward Compatibility
- Maintain existing function signatures where possible
- Provide fallback options for systems with limited resources
- Ensure GUI integration continues to work seamlessly

---

**Estimated Total Implementation Time:** 3-4 weeks
**Expected Performance Improvement:** 2-8x speedup depending on dataset size and hardware
**Risk Level:** Low to Medium with proper testing and phased implementation