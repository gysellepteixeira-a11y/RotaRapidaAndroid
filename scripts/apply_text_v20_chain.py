from pathlib import Path
import runpy

scripts = [
    'patch_v07.py','patch_v08.py','patch_v09.py','patch_v10.py','patch_v11.py','patch_v12.py','patch_v13.py','patch_v14.py','patch_v15.py','patch_v16.py','patch_v17.py','patch_v18.py','patch_v19.py','patch_v20.py','patch_v19_final.py',
    'patch_v19_stop_after_send.py','patch_v19_stop_read_fix.py','patch_v19_first_route_timing_fix.py','patch_v19_alerts_nonblocking.py','patch_v19_processing_reset.py','patch_v19_any_group.py','patch_v19_keep_ocr_warm.py','patch_v19_admin_locked_group.py','patch_v19_admin_lock_stable.py','patch_v19_admin_message_noise_fix.py','patch_v19_direct_mediastore_watch.py','patch_v19_mediastore_ignore_admin_toggle.py','patch_v19_speed_diagnostic.py','patch_v19_optimization1.py','patch_v19_dense_row_recovery.py','patch_v19_dense_recovery_compile_fix.py','patch_v19_dense_cage_unicode_fix.py','patch_v19_dense_recovery_marker.py','patch_v19_dense_recovery_fast_hint.py','patch_v19_dense_short_image.py','patch_v19_media25_preocr10.py','patch_v19_bairro_first_cage_second.py','patch_v19_cage_narrow.py','patch_v19_send_one_attempt.py','patch_v19_send_one_click_poll.py','patch_v19_send_wait_ready.py','patch_v19_send_ready_media10_statuslean.py','patch_v19_admin_ultra_10_6.py','patch_v19_admin_ultra_direct_fast.py','patch_v19_media10_statuslean_admin_direct_marker.py','patch_v19_text_diagnostic_old_base.py','patch_v19_text_diagnostic_compile_fix.py','patch_v19_text_first_old_base.py','patch_v19_image_bulk_pixels_v9.py','patch_v19_text_read_more_fast_v10.py','patch_v19_text_read_more_tree_v11.py','patch_v19_text_read_more_verified_v12.py','patch_v19_text_read_more_desc_direct_v14.py','patch_v19_text_read_more_newitem_guard_v15.py','patch_v19_text_read_more_expanded_bubble_v16.py','patch_v19_text_read_more_fresh_bubble_v17.py','patch_v19_text_read_more_strict_v18.py','patch_v19_text_read_more_desc_poll_v20.py'
]

base = Path('scripts')
for name in scripts:
    p = base / name
    if not p.exists():
        raise SystemExit(f'missing patch script: {name}')
    print(f'>>> applying {name}')
    runpy.run_path(str(p), run_name='__main__')

print('TEXT v20 chain complete')
