"""Manifest builder controller — constructs and signs an ota_manifest_t."""


def build_manifest(fw_path: str, key_path: str, out_path: str,
                   vendor_id: str, device_class: str,
                   major: int, minor: int, patch: int,
                   security_version: int, chunk_size: int,
                   logger) -> None:
    """Build and sign the manifest; log fields and save to disk."""
    from manifest_builder import ManifestBuilder, ManifestConfig, pack_version

    logger.section("Build Manifest")

    vendor = vendor_id.strip()[:4].ljust(4, "\x00").encode()
    dev_cls = device_class.strip()[:2].ljust(2, "\x00").encode()
    fw_ver = pack_version(major, minor, patch)

    logger.info(f"Firmware:         {fw_path}")
    logger.info(f"Private key:      {key_path}")
    logger.info(f"Version:          {major}.{minor}.{patch}")
    logger.info(f"Vendor/DevClass:  {vendor_id} / {device_class}")
    logger.info(f"Security version: {security_version}")
    logger.info(f"Chunk size:       {chunk_size} bytes")

    config = ManifestConfig(
        vendor_id=vendor,
        device_class=dev_cls,
        device_id=0,
        fw_version=fw_ver,
        security_version=security_version,
        chunk_size=chunk_size,
    )

    builder = ManifestBuilder(config, key_path)
    manifest = builder.build_from_file(fw_path)
    builder.save_manifest(manifest, out_path)

    info = ManifestBuilder.parse_manifest(manifest)
    logger.ok(f"Manifest saved → {out_path}")
    logger.ok(f"Manifest size:  {len(manifest)} bytes")
    logger.info("──── Manifest Fields ────")
    for k, v in info.items():
        logger.info(f"  {k:<20} = {v}")
