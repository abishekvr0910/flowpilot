# FlowPilot Open-Source Licensing & Third-Party Attribution Inventory

**Product:** FlowPilot Desktop v2.0.0  
**Classification:** Legal & Licensing Compliance Documentation  
**Date:** October 14, 2026  

FlowPilot integrates several high-performance open-source libraries. This document lists all third-party components, their respective licenses, and compliance statements.

---

## 1. Summary Licensing Table

| Component / Library | Version | License | Primary Purpose in FlowPilot |
|:---|:---|:---|:---|
| **Python** | 3.11.x | Python Software Foundation (PSF) | Core runtime environment |
| **PySide6 (Qt for Python)** | 6.x | LGPL v3 / Commercial | Native desktop GUI, Floating HUD, System Tray |
| **faster-whisper** | 1.x | MIT License | Local Whisper ASR inference pipeline |
| **CTranslate2** | 4.x | MIT License | High-performance C++ inference engine for Whisper |
| **sounddevice** | 0.4.x | MIT License | Windows CoreAudio recording via PortAudio |
| **PortAudio** | v19 | MIT-style License | Cross-platform audio I/O binding |
| **soundfile** | 0.12.x | BSD 3-Clause License | Audio WAV encoding and decoding |
| **libsndfile** | 1.x | LGPL v2.1 | Native audio file reading/writing library |
| **pycaw** | 2024.x | MIT License | Windows CoreAudio session ducking & volume control |
| **comtypes** | 1.x | MIT License | Windows COM automation interface for CoreAudio |
| **numpy** | 1.26.x / 2.x | BSD 3-Clause License | Real-time audio array buffering & linear resampling |
| **psutil** | 6.x | BSD 3-Clause License | Process inspection & memory tracking |
| **pywin32** | 308+ | PSF License | Native Win32 API (`RegisterHotKey`, `SendInput`) |
| **pyperclip** | 1.9.x | BSD 3-Clause License | System clipboard access |

---

## 2. LGPL v3 Compliance Statement (PySide6 / Qt)

FlowPilot utilizes **PySide6**, the official Python bindings for Qt 6, which is licensed under the GNU Lesser General Public License version 3 (**LGPL v3**).

In full compliance with LGPL v3 requirements:
1. **Dynamic Linking:** FlowPilot links dynamically to PySide6 and the Qt dynamic link libraries (`.dll`). The Qt libraries are not statically compiled into `FlowPilot.exe`.
2. **User Relinking Rights:** Any user may replace the bundled Qt/PySide6 dynamic link libraries located within the `_internal/PySide6/` directory with their own customized or recompiled versions of compatible Qt 6 libraries without modifying FlowPilot source code.
3. **No Qt Modifications:** FlowPilot uses upstream, unmodified PySide6 wheel distributions provided by The Qt Company.

---

## 3. License Texts & Copyright Notices

### MIT License
*Applicable to: faster-whisper, CTranslate2, sounddevice, pycaw, comtypes*
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:  
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

### BSD 3-Clause License
*Applicable to: soundfile, numpy, psutil, pyperclip*
> Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
> 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
> 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
> 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

### PortAudio License
> PortAudio Portable Audio Library. Copyright (c) 1999-2026 Ross Bencina and Phil Burk.  
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction...

### Python Software Foundation License
*Applicable to: Python runtime, pywin32*
> PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2  
> 1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and the Individual or Organization ("Licensee") accessing and otherwise using this software ("Python") in source or binary form and its associated documentation...

---

## 4. Proprietary & Application Code Notice

The proprietary business logic, deterministic writing intelligence algorithms, FactGuard™ verification routines, and custom UI implementations of FlowPilot are Copyright © 2026 FlowPilot Contributors.
