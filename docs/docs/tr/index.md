---
template: frontpage.html

hide:
  - toc
---

[![Sistem Demosu](https://img.youtube.com/vi/ZF_N-Vu7Tik/maxresdefault.jpg)](https://www.youtube.com/watch?v=ZF_N-Vu7Tik){ width="25%" height="auto" target="_blank" rel="noopener" }

# Nebula 2025 Drone Sistemi

## Sistem Mimarisi

<div class="grid cards" markdown>

-   ### :material-monitor: Yer Kontrol İstasyonu (YKS)
    ----

    Drone izleme, komut iletme ve görev takibi için birincil kontrol arayüzü

    **Temel Bileşenler**  
    - PySide6/QFluentWidgets UI çerçevesi  
    - MAVLink telemetri görselleştirme  
    - Görev planlama arayüzü  
    - Acil durum komut hattı  
    
    [:octicons-arrow-right-24: Modül Dokümantasyonu](gcs/index.md)

-   ### :material-connection: İletişim Sistemi
    ----

    Kenar sunucusu ve YKS arasındaki tüm modüller arası iletişimi yönetir

    **Temel Bileşenler**  
    - ZeroMQ mesaj aracısı  
    - Asyncio görev yöneticisi  
    - MAVLink protokol implementasyonu  
    
    [:octicons-arrow-right-24: Modül Dokümantasyonu](comms/index.md)

-   ### :material-brain: Görüntü İşleme
    ----

    Hedef tanımlama ve yük operasyonları için bilgisayarlı görü alt sistemi

    **Temel Bileşenler**  
    - YOLOv8 nesne tanıma  
    - OpenCV ön işleme  
    - GPS tahmin sistemi  
    
    [:octicons-arrow-right-24: Modül Dokümantasyonu](vision/index.md)

-   ### :material-airplane: Simülasyon
    ----

    Tam donanım-döngüde test ortamı

    **Temel Bileşenler**  
    - Gazebo ortamı  
    - ArduPilot SITL  
    - Sensör emülasyonu  
    
    [:octicons-arrow-right-24: Modül Dokümantasyonu](simulation/index.md)
</div>


<div class="" markdown style="padding: 0 1em 0 1em;">
[LİSANS](LICENSE.md) | [Hata Takipçisi](https://github.com/amar-jay/nebula/issues)
</div>

## Proje Genel Bakış

Bu dokümantasyon, [Teknofest 2025 Drone Yarışması](https://www.teknofest.org) için geliştirilen Nebula 2025 otonom drone sistemini kapsamaktadır. Sistem özellikleri:

- PySide6 tabanlı Yer Kontrol İstasyonu ile gerçek zamanlı drone kontrolü
- ZeroMQ iletişimli kenar bilişim işleme
- Uçuş kontrolü için ArduPilot entegrasyonu
- Paket yükleme operasyonları için bilgisayarlı görü
- Gazebo simülasyon ortamı

## Teknofest Hakkında

[Teknofest](https://www.teknofest.org), Türkiye'nin önde gelen havacılık ve teknoloji festivalidir. Çoklu mühendislik disiplinlerinde yarışma kategorileri bulunur. 10 üyeli ekibimiz bu sistemi, otonom paket teslimi ve nesne tanıma görevlerine odaklanan drone yarışması kategorisi için geliştirmiştir.

### Teknik Yazılım Liderliği
Dokümantasyon ve sistem mimarisi [amarjay](https://github.com/amar-jay) tarafından yönetilmektedir

---

## Teknik Özellikler
| Bileşen              | Sürüm         | Bağımlılıklar          |
|----------------------|---------------|------------------------|
| Uçuş Kontrolcüsü     | ArduPilot Copter 4.3 | Ardupilot SDK  |
| İletişim Protokolü   | MAVLink 2.0   | pymavlink 2.4.37      |
| Kenar İşletim Sistemi| Ubuntu 22.04  | Python 3.10  |
| Görüntü İşleme Altyapısı | YOLOv8    | OpenCV, PyTorch      |
| YKS Çerçevesi        | PySide6       | QFluentWidgets [(amar-jay's fork)](https://github.com/amar-jay/QFluentWidgets)   |

## Başlarken
```bash
git clone --recurse-submodules https://github.com/amar-jay/nebula.git
cd nebula
git submodule update --init --recursive
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make run_sim  # Simülasyonu başlat
make app      # Kontrol istasyonunu çalıştır
make sim_server # Kenar sunucusunu başlat (simülasyon modu)
```