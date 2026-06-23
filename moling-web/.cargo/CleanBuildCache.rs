//! Cargo build cache cleaner
//! 在 `cargo build` 前运行，清理上次构建残留。
//! 用法: cargo run --manifest-path .cargo/CleanBuildCache.toml
//! 或:    cargo clean-build-cache   (通过 .cargo/config.toml alias)

use std::fs;
use std::path::Path;

fn main() {
    let target = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("src-tauri")
        .join("target");

    if !target.exists() {
        println!("target/ 不存在，跳过");
        return;
    }

    // 1. 清 debug/build/ 下非当前依赖的旧产物
    let build_dir = target.join("debug").join("build");
    if build_dir.exists() {
        match fs::read_dir(&build_dir) {
            Ok(entries) => {
                let mut removed = 0u64;
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_dir() {
                        // 检查是否有 .rustc_info.json (cargo 标记为活跃)
                        if !path.join(".rustc_info.json").exists() {
                            if let Ok(meta) = fs::metadata(&path) {
                                if let Ok(_) = fs::remove_dir_all(&path) {
                                    removed += meta.len();
                                }
                            }
                        }
                    }
                }
                if removed > 0 {
                    println!(
                        "清理 build 缓存: {} MB",
                        removed / 1024 / 1024
                    );
                }
            }
            Err(e) => eprintln!("读取 build/ 失败: {}", e),
        }
    }

    // 2. 清 .fingerprint/ 中孤立条目
    let fp_dir = target.join("debug").join(".fingerprint");
    if fp_dir.exists() {
        if let Ok(entries) = fs::read_dir(&fp_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                // 清理 7 天前的指纹文件
                if let Ok(meta) = fs::metadata(&path) {
                    if let Ok(age) = meta.modified().map(|t| t.elapsed().unwrap_or_default())
                    {
                        if age.as_secs() > 7 * 86400 {
                            let _ = fs::remove_file(&path);
                        }
                    }
                }
            }
        }
    }

    println!("构建缓存清理完成");
}
