# app_entry_rca_v1 corrected FTA leaf taxonomy

- Candidate groups: 25
- Leaf nodes: 151
- Automatic rules: 41

P1-P7 are canonical app-entry timeline phases. P8 is cross-cutting evidence only.

## P1 Touch Duration

### Input event window (`p1.touch_duration.input_event_window`)
- `p1.touch_duration.input_event_window.touch_down` — touch down
- `p1.touch_duration.input_event_window.touch_up` — touch up
- `p1.touch_duration.input_event_window.touch_down_to_touch_up` — touch down -> touch up

### system_server input dispatch (`p1.touch_duration.system_server_input_dispatch`)
- `p1.touch_duration.system_server_input_dispatch.inputdispatcher_notify_motion` — InputDispatcher::notifyMotion
- `p1.touch_duration.system_server_input_dispatch.dispatch_motion_locked` — dispatchMotionLocked
- `p1.touch_duration.system_server_input_dispatch.find_touched_window_targets` — findTouchedWindowTargets
- `p1.touch_duration.system_server_input_dispatch.prepare_dispatch_cycle_locked` — prepareDispatchCycleLocked
- `p1.touch_duration.system_server_input_dispatch.enqueue_dispatch_entry_and_start_dispatch_cycle_locked` — enqueueDispatchEntryAndStartDispatchCycleLocked
- `p1.touch_duration.system_server_input_dispatch.start_dispatch_cycle_locked` — startDispatchCycleLocked
- `p1.touch_duration.system_server_input_dispatch.publish_motion_event_down` — publishMotionEvent(action=DOWN)
- `p1.touch_duration.system_server_input_dispatch.publish_motion_event_up` — publishMotionEvent(action=UP)

### Launcher input handling (`p1.touch_duration.launcher_input_handling`)
- `p1.touch_duration.launcher_input_handling.deliver_input_event` — deliverInputEvent
- `p1.touch_duration.launcher_input_handling.launcher_click_handler` — Launcher click handler
- `p1.touch_duration.launcher_input_handling.active_launch` — ActiveLaunch
- `p1.touch_duration.launcher_input_handling.launcher_start_activity` — launcher startActivity

## P2 Launch Preparation

### P2-1 system_server + launcher workflow (`p2.launch_preparation.system_server_launcher_workflow`)
- `p2.launch_preparation.system_server_launcher_workflow.start_activity` — startActivity
- `p2.launch_preparation.system_server_launcher_workflow.iatms_startactivity_server` — IActivityTaskManager::startActivity server side
- `p2.launch_preparation.system_server_launcher_workflow.should_abort_background_activity_start` — shouldAbortBackgroundActivityStart
- `p2.launch_preparation.system_server_launcher_workflow.start_activity_inner` — startActivityInner
- `p2.launch_preparation.system_server_launcher_workflow.activity_pause` — activityPause
- `p2.launch_preparation.system_server_launcher_workflow.perform_pause` — performPause
- `p2.launch_preparation.system_server_launcher_workflow.launcher_on_pause` — Launcher onPause
- `p2.launch_preparation.system_server_launcher_workflow.wms_transition_setup` — WMS / transition setup
- `p2.launch_preparation.system_server_launcher_workflow.client_transaction_construction` — ClientTransaction construction
- `p2.launch_preparation.system_server_launcher_workflow.lifecycle_transaction_delivery` — lifecycle transaction delivery

### P2-2 target app process launch (`p2.launch_preparation.target_app_process_launch`)
- `p2.launch_preparation.target_app_process_launch.process_start_request` — process start request
- `p2.launch_preparation.target_app_process_launch.start_proc` — Start proc
- `p2.launch_preparation.target_app_process_launch.zygote_fork` — process fork
- `p2.launch_preparation.target_app_process_launch.post_fork` — PostFork
- `p2.launch_preparation.target_app_process_launch.zygote_init` — ZygoteInit
- `p2.launch_preparation.target_app_process_launch.activity_thread_main` — ActivityThreadMain
- `p2.launch_preparation.target_app_process_launch.app_process_scheduling` — app process scheduling
- `p2.launch_preparation.target_app_process_launch.activity_thread_attach` — ActivityThread.attach

## P3 bindApplication / activityStart

### Framework bindApplication dispatch (`p3.bindapplication_activitystart.framework_bind_application`)
- `p3.bindapplication_activitystart.framework_bind_application.iapplicationthread_bindapplication_server` — IApplicationThread::bindApplication server side
- `p3.bindapplication_activitystart.framework_bind_application.bind_application` — bindApplication
- `p3.bindapplication_activitystart.framework_bind_application.handle_bind_application` — ActivityThread handleBindApplication
- `p3.bindapplication_activitystart.framework_bind_application.resources_apply_configuration` — ResourcesManager#applyConfigurationToResources
- `p3.bindapplication_activitystart.framework_bind_application.classloader_namespace` — createClassloaderNamespace
- `p3.bindapplication_activitystart.framework_bind_application.setup_graphics_support` — setupGraphicsSupport
- `p3.bindapplication_activitystart.framework_bind_application.setup_proxies` — Setup proxies

### Application creation and startup (`p3.bindapplication_activitystart.app_creation_and_startup`)
- `p3.bindapplication_activitystart.app_creation_and_startup.make_application` — makeApplication
- `p3.bindapplication_activitystart.app_creation_and_startup.application_attach` — Application attach
- `p3.bindapplication_activitystart.app_creation_and_startup.application_oncreate` — Application onCreate
- `p3.bindapplication_activitystart.app_creation_and_startup.app_startup` — app Startup

### Runtime/resource bootstrap during bindApplication (`p3.bindapplication_activitystart.runtime_and_resource_bootstrap`)
- `p3.bindapplication_activitystart.runtime_and_resource_bootstrap.open_dex_files_from_oat` — OpenDexFilesFromOat
- `p3.bindapplication_activitystart.runtime_and_resource_bootstrap.appimage_loading` — AppImage:Loading
- `p3.bindapplication_activitystart.runtime_and_resource_bootstrap.class_loading_dex_resource_loading` — class loading / dex / resource loading
- `p3.bindapplication_activitystart.runtime_and_resource_bootstrap.load_apk_assets` — LoadApkAssets / ApkAssets
- `p3.bindapplication_activitystart.runtime_and_resource_bootstrap.loaded_arsc` — LoadedArsc / LoadedPackage parsing
- `p3.bindapplication_activitystart.runtime_and_resource_bootstrap.native_linker_dlopen` — native linker / dlopen / JNI_OnLoad

## P4 activityStart / activityResume

### Activity start lifecycle (`p4.activitystart_activityresume.activity_lifecycle_start`)
- `p4.activitystart_activityresume.activity_lifecycle_start.activity_start` — activityStart
- `p4.activitystart_activityresume.activity_lifecycle_start.lifecycle_transaction` — lifecycle transaction
- `p4.activitystart_activityresume.activity_lifecycle_start.perform_launch_activity` — performLaunchActivity
- `p4.activitystart_activityresume.activity_lifecycle_start.perform_create` — performCreate:<Activity>
- `p4.activitystart_activityresume.activity_lifecycle_start.activity_attach` — Activity attach
- `p4.activitystart_activityresume.activity_lifecycle_start.activity_oncreate` — Activity onCreate
- `p4.activitystart_activityresume.activity_lifecycle_start.app_handle_start` — APP_handleStart
- `p4.activitystart_activityresume.activity_lifecycle_start.saved_state_restore` — saved-state restore

### Activity UI/resource creation (`p4.activitystart_activityresume.activity_ui_creation`)
- `p4.activitystart_activityresume.activity_ui_creation.inflate` — inflate
- `p4.activitystart_activityresume.activity_ui_creation.init_manager` — initManager
- `p4.activitystart_activityresume.activity_ui_creation.create_base_activity_resources` — ResourcesManager#createBaseActivityResources
- `p4.activitystart_activityresume.activity_ui_creation.theme_apply_style` — Theme::ApplyStyle
- `p4.activitystart_activityresume.activity_ui_creation.assetmanager_open_xml_asset` — AssetManager::OpenXmlAsset
- `p4.activitystart_activityresume.activity_ui_creation.view_creation` — view creation
- `p4.activitystart_activityresume.activity_ui_creation.fragment_or_compose_construction` — Fragment / Compose construction
- `p4.activitystart_activityresume.activity_ui_creation.first_visible_content_setup` — first visible content setup

### activityStart handoff and scheduling (`p4.activitystart_activityresume.activitystart_handoff_and_scheduling`)
- `p4.activitystart_activityresume.activitystart_handoff_and_scheduling.activitystart_gate_gap` — activityStart gate gap
- `p4.activitystart_activityresume.activitystart_handoff_and_scheduling.app_main_thread_scheduling` — app main thread scheduling
- `p4.activitystart_activityresume.activitystart_handoff_and_scheduling.binder_or_lock_wait_before_oncreate` — binder / lock wait before onCreate

## P5 activityResume / first Choreographer#doFrame

### Activity resume lifecycle (`p5.activityresume_first_choreographerdoframe.activity_resume_lifecycle`)
- `p5.activityresume_first_choreographerdoframe.activity_resume_lifecycle.activity_resume` — activityResume
- `p5.activityresume_first_choreographerdoframe.activity_resume_lifecycle.perform_resume` — performResume:<Activity>
- `p5.activityresume_first_choreographerdoframe.activity_resume_lifecycle.activity_onresume` — Activity onResume
- `p5.activityresume_first_choreographerdoframe.activity_resume_lifecycle.lifecycle_callback` — lifecycle callback
- `p5.activityresume_first_choreographerdoframe.activity_resume_lifecycle.activity_resumed_server` — IActivityClientController::activityResumed server side

### Post-resume app work (`p5.activityresume_first_choreographerdoframe.post_resume_app_work`)
- `p5.activityresume_first_choreographerdoframe.post_resume_app_work.main_thread_work_after_resume` — app main thread work after resume
- `p5.activityresume_first_choreographerdoframe.post_resume_app_work.binder_io_lock_in_onresume` — binder / I/O / lock contention in onResume
- `p5.activityresume_first_choreographerdoframe.post_resume_app_work.observer_or_callback_dispatch` — observer / callback dispatch
- `p5.activityresume_first_choreographerdoframe.post_resume_app_work.first_frame_request_from_resume` — first frame request from resume

## P6 first Choreographer#doFrame / activityIdle

### Frame scheduling and VSync (`p6.first_choreographerdoframe_activityidle.frame_scheduling_and_vsync`)
- `p6.first_choreographerdoframe_activityidle.frame_scheduling_and_vsync.first_choreographer_doframe` — Choreographer#doFrame
- `p6.first_choreographerdoframe_activityidle.frame_scheduling_and_vsync.schedule_traversals` — scheduleTraversals
- `p6.first_choreographerdoframe_activityidle.frame_scheduling_and_vsync.vsync_callback` — VSync callback
- `p6.first_choreographerdoframe_activityidle.frame_scheduling_and_vsync.main_looper_backlog` — main Looper / message backlog
- `p6.first_choreographerdoframe_activityidle.frame_scheduling_and_vsync.missed_vsync_before_traversal` — missed VSync before traversal

### View traversal and draw (`p6.first_choreographerdoframe_activityidle.view_traversal_and_draw`)
- `p6.first_choreographerdoframe_activityidle.view_traversal_and_draw.traversal` — traversal
- `p6.first_choreographerdoframe_activityidle.view_traversal_and_draw.measure` — measure
- `p6.first_choreographerdoframe_activityidle.view_traversal_and_draw.layout` — layout
- `p6.first_choreographerdoframe_activityidle.view_traversal_and_draw.draw` — draw
- `p6.first_choreographerdoframe_activityidle.view_traversal_and_draw.draw_vri` — draw-VRI
- `p6.first_choreographerdoframe_activityidle.view_traversal_and_draw.record_view_draw` — Record View#draw
- `p6.first_choreographerdoframe_activityidle.view_traversal_and_draw.relayoutwindow_first_true` — relayoutWindow#first=true
- `p6.first_choreographerdoframe_activityidle.view_traversal_and_draw.repeated_measure_or_layout` — repeated measure/layout pass

### Surface / RenderThread / GPU path (`p6.first_choreographerdoframe_activityidle.surface_and_renderthread`)
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.create_surface_control` — createSurfaceControl
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.isurfacecomposerclient_create_surface` — ISurfaceComposerClient::createSurface
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.renderthread_drawframes` — RenderThread DrawFrames
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.sync_and_draw_frame` — SyncAndDrawFrame
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.vulkan_finish_frame` — Vulkan finish frame
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.texture_or_glyph_upload` — texture / glyph upload
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.buffer_allocate_or_dequeue` — GraphicBuffer allocate / dequeueBuffer
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.surfaceflinger_hwc` — SurfaceFlinger / HWC
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.gpu_fence_wait` — GPU / fence wait
- `p6.first_choreographerdoframe_activityidle.surface_and_renderthread.frame_or_vsync` — frame / vsync

## P7 activityIdle

### activityIdle reporting (`p7.activityidle.activityidle_reporting`)
- `p7.activityidle.activityidle_reporting.activity_idle` — activityIdle
- `p7.activityidle.activityidle_reporting.activity_idle_client` — activityIdle client
- `p7.activityidle.activityidle_reporting.activity_idle_binder_delivery` — client-to-system_server activityIdle Binder delivery
- `p7.activityidle.activityidle_reporting.activity_idle_server` — IActivityClientController::activityIdle server side
- `p7.activityidle.activityidle_reporting.system_server_idle_reporting` — system_server idle reporting
- `p7.activityidle.activityidle_reporting.activitytaskmanager_state_transition` — ActivityTaskManager state transition
- `p7.activityidle.activityidle_reporting.window_surface_placer` — WindowSurfacePlacer
- `p7.activityidle.activityidle_reporting.window_animator` — WindowAnimator
- `p7.activityidle.activityidle_reporting.activity_idle_monitor_contention` — system_server activityIdle monitor / lock contention

### Post-first-frame tail (`p7.activityidle.post_first_frame_tail`)
- `p7.activityidle.post_first_frame_tail.post_first_frame_tail_to_activityidle` — post-first-frame tail to activityIdle
- `p7.activityidle.post_first_frame_tail.repeated_choreographer_doframe` — repeated Choreographer#doFrame
- `p7.activityidle.post_first_frame_tail.recyclerview_onlayout` — RecyclerView OnLayout
- `p7.activityidle.post_first_frame_tail.recyclerview_onbindview` — RecyclerView OnBindView
- `p7.activityidle.post_first_frame_tail.adapter_or_list_update` — adapter / list update
- `p7.activityidle.post_first_frame_tail.vectordrawable_repaint` — VectorDrawable repaint
- `p7.activityidle.post_first_frame_tail.idlehandler_or_messagequeue_work` — IdleHandler / MessageQueue work
- `p7.activityidle.post_first_frame_tail.reportfullydrawn_or_custom_ready` — reportFullyDrawn / custom-ready delay

### Measurement endpoint validation (`p7.activityidle.measurement_endpoint_validation`)
- `p7.activityidle.measurement_endpoint_validation.first_frame_vs_activityidle_endpoint` — first frame vs activityIdle endpoint
- `p7.activityidle.measurement_endpoint_validation.wrong_activity_marker` — marker belongs to wrong Activity
- `p7.activityidle.measurement_endpoint_validation.different_dut_ref_endpoint_policy` — different DUT/REF endpoint policy

## P8 Cross-cutting System Evidence

### CPU scheduling and runnable latency (`p8.cross_cutting_system_evidence.cpu_scheduling`)
- `p8.cross_cutting_system_evidence.cpu_scheduling.critical_runnable_latency` — critical thread runnable latency
- `p8.cross_cutting_system_evidence.cpu_scheduling.same_cpu_blocker` — runnable thread -> CPU blocker
- `p8.cross_cutting_system_evidence.cpu_scheduling.irq_softirq_kworker_pressure` — IRQ / softirq / kworker pressure
- `p8.cross_cutting_system_evidence.cpu_scheduling.cpu_frequency_or_dvfs` — CPU frequency / DVFS
- `p8.cross_cutting_system_evidence.cpu_scheduling.thermal_or_power_cap` — thermal / power cap

### Binder / lock dependency (`p8.cross_cutting_system_evidence.binder_lock_dependency`)
- `p8.cross_cutting_system_evidence.binder_lock_dependency.binder_client_to_server` — Binder client -> server
- `p8.cross_cutting_system_evidence.binder_lock_dependency.binder_thread_pool_saturation` — Binder thread-pool saturation
- `p8.cross_cutting_system_evidence.binder_lock_dependency.waiter_to_lock_owner` — waiter -> lock owner
- `p8.cross_cutting_system_evidence.binder_lock_dependency.monitor_or_futex_contention` — monitor / futex contention

### I/O, page fault and storage (`p8.cross_cutting_system_evidence.io_page_fault_storage`)
- `p8.cross_cutting_system_evidence.io_page_fault_storage.file_backed_page_fault` — file-backed page fault
- `p8.cross_cutting_system_evidence.io_page_fault_storage.block_device_latency` — block device queue/service latency
- `p8.cross_cutting_system_evidence.io_page_fault_storage.filesystem_or_page_lock` — filesystem / inode / page-cache lock
- `p8.cross_cutting_system_evidence.io_page_fault_storage.background_io_contention` — background I/O contention

### Memory, GC and reclaim (`p8.cross_cutting_system_evidence.memory_gc_reclaim`)
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.wait_for_gc_to_complete` — WaitForGcToComplete
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.stw_gc_pause` — STW GC pause
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.allocation_stall` — allocation stall
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.direct_reclaim` — direct reclaim
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.kswapd_competition` — kswapd competition
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.compaction_stall` — compaction stall
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.zram_or_swap` — zram / swap
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.lmkd_or_process_restart` — lmkd / process restart
- `p8.cross_cutting_system_evidence.memory_gc_reclaim.gc_overlap_only` — GC overlap only

### System render/GPU evidence (`p8.cross_cutting_system_evidence.render_gpu_system`)
- `p8.cross_cutting_system_evidence.render_gpu_system.renderthread_runnable_latency` — RenderThread runnable latency
- `p8.cross_cutting_system_evidence.render_gpu_system.surfaceflinger_delay` — SurfaceFlinger delay
- `p8.cross_cutting_system_evidence.render_gpu_system.gpu_fence_wait` — GPU / fence wait
- `p8.cross_cutting_system_evidence.render_gpu_system.hwc_present_delay` — HWC present delay

### Test environment / config difference (`p8.cross_cutting_system_evidence.test_environment_config`)
- `p8.cross_cutting_system_evidence.test_environment_config.trace_overhead` — Perfetto / logging overhead
- `p8.cross_cutting_system_evidence.test_environment_config.package_state_or_cache_difference` — package state / cache difference
- `p8.cross_cutting_system_evidence.test_environment_config.display_refresh_rate_difference` — display refresh-rate difference
- `p8.cross_cutting_system_evidence.test_environment_config.automation_timing_difference` — automation timing difference
