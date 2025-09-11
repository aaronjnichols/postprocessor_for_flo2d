# FLO-2D Postprocessor Deployment Guide

This project no longer ships a standalone executable or Windows installer. Deploy and run via a standard Python environment.

## Recommended Deployment

- Use `scripts\setup.bat` on Windows to create a virtual environment and install dependencies.
- Distribute the repository (or a tagged release zip) and instruct users to run the GUI or CLI with Python.

### Prerequisites
- Python 3.8+
- pip

### Install
```bash
pip install -r requirements.txt
# Optional: tests
pip install -r test-requirements.txt
```

### Run
```bash
# GUI
python gui/launch_gui.py

# CLI
python main.py -h
```

## Testing and Validation

Focus on functional testing in the Python environment:
- GUI launches and workflows complete without errors
- CLI processes representative FLO-2D projects and generates expected outputs
- Outputs (GeoPackage/GeoTIFF/Excel/PDF) open correctly in target tools

#### Functional Testing
- [ ] All major FLO-2D file types processed
- [ ] GUI controls work as expected
- [ ] Configuration saves and loads
- [ ] Progress tracking functions
- [ ] Error messages are user-friendly
- [ ] Output files are valid and properly formatted

### Test Environments

Minimum suggested:
- Windows 10/11
- 4 GB RAM
- 1 GB free disk space

**Recommended Testing:**
- Windows 10 and 11 (both clean and with existing Python)
- Different user privilege levels (admin and standard user)
- Various FLO-2D model sizes (small, medium, large)
- Different coordinate systems and file configurations

## Distribution Strategy

### GitHub Releases

1. **Create Release Tag**
   ```bash
   git tag -a v1.0.0 -m "Version 1.0.0 - Initial public release"
   git push origin v1.0.0
   ```

2. **Upload Assets**
   - `FLO2D-Postprocessor-Setup.exe` (installer)
   - `FLO2D-Postprocessor.exe` (standalone executable)
   - `Source code.zip` (GitHub auto-generates)

3. **Release Notes**
   - Include changelog
   - List system requirements
   - Provide installation instructions
   - Include known issues

### Distribution Checklist

- [ ] Version numbers updated in all files
- [ ] CHANGELOG.md updated
- [ ] README.md reflects current features
- [ ] All hardcoded paths removed
- [ ] License file included
- [ ] Documentation complete
- [ ] Example configuration provided
- [ ] Build scripts tested
- [ ] Executables tested on clean systems
- [ ] File sizes reasonable (< 100MB for executable)

## Maintenance and Updates

### Version Management

Use semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

Update version in:
- `version.py`
- `build_exe.py`
- `installer.iss`
- `README.md`
- `CHANGELOG.md`

### Update Process

1. **Fix issues or add features**
2. **Update version numbers**
3. **Update documentation**
4. **Run full test suite**
5. **Build new executable and installer**
6. **Test on clean systems**
7. **Create GitHub release**
8. **Update distribution channels**

### Automated Builds (Future Enhancement)

Consider GitHub Actions for automated building:
- Trigger builds on tag creation
- Build executables for multiple platforms
- Run tests automatically
- Upload releases automatically

## Security Considerations

### Code Signing (Optional but Recommended)

For public distribution, consider code signing:
- Prevents Windows security warnings
- Builds user trust
- Requires certificate from trusted CA
- Can be expensive for individual developers

### Antivirus False Positives

Standalone executables sometimes trigger antivirus warnings:
- Submit to major antivirus vendors for whitelisting
- Use VirusTotal to check detection rates
- Consider code signing to reduce false positives
- Document known issues in README

## File Structure for Release

```
release_package/
├── FLO2D-Postprocessor-Setup.exe    # Windows installer
├── FLO2D-Postprocessor.exe          # Standalone executable  
├── README.md                         # Installation guide
├── LICENSE                           # MIT license
├── CHANGELOG.md                      # Version history
├── docs/
│   ├── USER_MANUAL.md               # User documentation
│   └── TROUBLESHOOTING.md           # Common issues
└── examples/
    ├── config.example.json          # Example configuration
    └── sample_data/                 # Sample FLO-2D files (if available)
```

## Support Strategy

Since this is a "no contributors wanted" project:

1. **Issues Tracking**: Set GitHub issues to read-only or disable
2. **Documentation**: Provide comprehensive guides
3. **FAQ**: Include common questions and answers
4. **Contact**: Provide limited support channel if desired
5. **Community**: Consider allowing community-driven documentation

## Legal Considerations

- **MIT License**: Allows free use and modification
- **Disclaimer**: Include "provided as-is" language
- **Third-party**: Acknowledge all used libraries
- **FLO-2D**: Include disclaimer about FLO-2D Software, Inc.

---

This deployment guide ensures a professional, reliable release process that provides value to the FLO-2D modeling community while minimizing maintenance burden.
