---
title: Yer Kontrol İstasyonu (GCS)
description: Nebula Yer Kontrol İstasyonu dokümantasyonu, kullanıcı arayüzü tasarımı, harita işlevselliği, kamera akışı, telemetri, görev planlama ve DroneClient mimarisini kapsar.

date: 2025-07-13

---

# Yer Kontrol İstasyonu (GCS)

**Nebula Yer İstasyonu**, uçuş kontrolü, telemetri izleme, görev planlama ve video işleme gibi işlevleri tek bir tutarlı ve görsel arayüzde birleştiren sistemimizin son halkasıdır. [**PySide6**](https://doc.qt.io/qtforpython-6/gettingstarted.html#getting-started) kullanılarak geliştirilen bu uygulama, Qt için Fluent Design System uyarlaması olan [**QFluentWidget**](https://qfluentwidgets.com/)'ın estetik ve tasarım felsefesini benimsemiştir. Ancak, QFluentWidget'ın Linux'ta PySide6 altında çalıştırılması sırasında bazı tutarsızlıklarla karşılaşılmıştır. Bu sorunları gidermek için bir fork oluşturulmuş, UI hataları düzeltilmiş ve Linux desteği iyileştirilmiştir. Bu fork şurada bulunabilir: [QFluentWidgets Fork](https://github.com/amar-jay/QFluentWidgets).

Sonuç, eşzamanlı drone verileri, ham video akışları ve canlı telemetriyi yönetirken bile kullanıcı dostu, duyarlı ve estetik bir masaüstü deneyimi sunan bir arayüzdür.

---

## Harita

**Harita** bölümü, Nebula Yer İstasyonu'nun kullanıcı arayüzünün merkezinde yer alır. Rolü, drone'un mevcut konumunu göstermenin ötesine geçerek mekansal akıl yürütme, görev oluşturma ve gerçek zamanlı durum farkındalığı için bir tuval sunar.

Harita açıldığında, kullanıcılar operasyonel sahadaki önemli varlıkları temsil eden dinamik güncellenen işaretleyicilerle karşılaşır:

- Telemetri ile güncellenen drone'un **mevcut konumu**.
    
- Kolay dönüş (RTL) mantığı için işaretlenmiş **ana üs**.
    
- Özel görev senaryoları için ayrılmış bir **kamikaze drone** işaretleyicisi.
    
- Müdahale veya eskort görevleri sırasında kullanılan bir **hedef drone** işaretleyicisi.
    

Bu işaretleyicilerin her biri işlevsel bir role sahiptir. Örneğin, otomatik dönüş veya hedef edinme gibi bazı komutlar, bu işaretleyicilerle ilişkilendirilmiş gerçek zamanlı GPS koordinatlarına bağlıdır.

Pasif izlemenin yanı sıra, harita **doğrudan etkileşime** de olanak tanır. Kullanıcılar manuel olarak haritaya bir yol noktası ekleyerek drone'u o konuma yönlendirebilir. Bu, **yol noktası görev sistemi**mizin temelini oluşturur ve birden fazla yol noktasının sıralı olarak eklenerek bir görev yolu oluşturulmasına imkan verir. Bu yol noktaları otomatik olarak **Görev Sekmesi** ile senkronize edilir ve burada düzenlenebilir veya gönderilebilir.

Bu mekanizma, özellikle önceden tanımlanmış alım ve bırakma noktalarına sahip **kargo teslimat görevleri** için kullanışlıdır. Daha detaylı bilgi ve tasarım motivasyonu için [proje planımıza](/project-plan) göz atabilirsiniz.

Harita ayrıca **coğrafi sınırlama** (geofencing) desteği sunar. Bu, kullanıcıların drone'un kalması gereken sanal bir sınır çizmesine olanak tanır. Testler sırasında güvenlik ve düzenlemelere uyum için özellikle yararlıdır. Drone bu sınırın ötesine geçmeye çalışırsa, yazılım tabanlı kontroller müdahale edebilir veya operatörü uyarabilir.

Esneklik sağlamak için, kullanıcılara **tüm işaretleyicileri temizleme**, **son işlemi geri alma** veya planlama tuvalini sıfırlama araçları sunulur.

---

## Sekmeler

### Kamera Sekmesi: Akış, Kayıt ve Gerçek Zamanlı İşleme

**Kamera Sekmesi**, uygulamanın teknik olarak en zorlu ancak kritik bileşenlerinden biridir. Drone'dan canlı video izlemeye olanak tanırken aynı zamanda nesne tespiti, iniş pisti tanımlama veya arazi haritalama gibi bilgisayarlı görü görevleri için işlenmiş görüntüler sunar.

Mevcut video akışı, **standart JPEG kodlaması** ile sağlanmaktadır. Modern codec'ler (H.264 veya H.265) ile karşılaştırıldığında verimsiz görünse de, JPEG burada pratik ve zaman açısından verimli bir çözümdür. `QImage` ile doğrudan entegre olarak harici çözücü ihtiyacı olmadan sorunsuz bir görüntüleme sağlar—bu, platformlar arası basitlik ve sınırlı geliştirme süresi göz önüne alındığında önemli bir avantajdır.

Video verileri, drone'un bilgi işlem düğümünde çalışan bir **ZeroMQ (ZMQ)** sunucusundan alınır. Arka planda çalışan bir `QThread` olarak başlatılan `DroneClient` örneği, bu video verilerini sürekli olarak almak ve çözmekle sorumludur. Kamera Sekmesi açık olmasa bile video akışı arka planda aktif olarak alınır. Bu, sekmeye geçiş yapıldığında veya kayıt başlatıldığında gecikme olmamasını sağlar.

Ancak, videonun GUI'ye yansıtılması kullanıcının "Bağlan" butonuna basmasına bağlıdır. Bu, **bant genişliği kontrolü ve kullanıcı tetiklemeli görüntüleme** sağlar.

/// uyarı | Not
Kullanıcı video sekmesinin bağlantısını kestiğinde, yalnızca görüntülemeyi durdururuz—**thread'i sonlandırmayız**. Bu ayrım kritiktir: video akışı arka planda akmaya devam eder ve ZMQ bağlantısı sürer, çünkü bu bağlantı diğer bileşenler için komutlar, telemetri ve meta verileri de taşır.
///

Kamera modülü ayrıca **video kaydını** destekler. Bu, OpenCV ile gerçekleştirilir. Alınan kareler bir video dosyasına eklenir. Kullanıcılar kaydı duraklatabilir veya sürdürebilir. Bu, modülü yalnızca canlı izleme için değil, aynı zamanda veri toplama ve çevrimdışı hata ayıklama için de çok yönlü hale getirir.

---

### Telemetri Sekmesi: Uçuş Dinamikleri için Görsel Geri Bildirim

**Telemetri Sekmesi**, ham sayısal telemetriyi okunabilir ve dinamik göstergelere dönüştürür. Pilotun drone'un iç durumunu görmesini sağlar.

Yükseklik, yön, hız ve pil seviyeleri görsel temsillere dönüştürülür:

- Bir **gösterge paneli**, gerçek zamanlı hız, yükseklik ve yönü gösterir.
    
- Bir **yapay ufuk**, drone'un eğim ve yatışını anlamak için önemlidir.
    
- Bir **pusula** ve koordinat beslemesi, yön ve coğrafi konumu takip eder.
    

Bu sekmedeki her öğe, `DroneClient` tarafından asenkron olarak alınan verilerle gerçek zamanlı olarak güncellenir. Amacı iki yönlüdür: pilotlara hızlı ve okunabilir bilgiler sunmak ve operatörlerin kalkış, iniş veya manevra sırasında anormallikleri tespit etmesini sağlamak.

---

### Görev Sekmesi: Planlama, Kontrol ve Otonomi

Harita ile sıkı bir şekilde bağlantılı olan **Görev Sekmesi**, kullanıcıların görev yol noktalarını incelemesine, düzenlemesine ve göndermesine olanak tanır.

Haritaya eklenen her yol noktası **Görev Tablosu**'nda görünür, ancak kullanıcılar buraya manuel olarak GPS koordinatları da ekleyebilir—bu, özellikle önceden tanımlanmış görev şablonlarını kullanırken veya diğer kaynaklardan rota kopyalarken idealdir.

Buradaki en güçlü özelliklerden biri **Otomatik Geçiş**'tir. Bu kontrol, görüntü tanıma tabanlı stabilizasyonu etkinleştirmek için bir anahtar görevi görür. Drone'un **kargo hedefleri** (helipad veya konteynerler gibi) üzerinde hizalanmasını sağlar. Etkinleştirildiğinde, drone kamera geri bildirimini kullanarak hedefin üzerinde merkezlenene kadar manevra yapar ve kargo alım operasyonları için güvenilirliği artırır.

Bu, tam otonomiye doğru atılan bir adımdır—kritik kargo işlemleri için manuel pilotaj ihtiyacını azaltır.

---

### Görev Konsolu: Günlük Kaydı ve Hata Ayıklama

Ana sekmelerin altında yer alan **Görev Konsolu**, uygulama yığını boyunca sistem olaylarını toplayan bir metin günlükçüdür.

Şunları kaydeder:

- Drone'a gönderilen komutlar
    
- Yol noktası güncellemeleri
    
- ZMQ iletişim durumu
    
- Kamera akış durumu
    
- Arka plan thread aktivitesi
    

Bu konsol öncelikle **geliştiriciler ve testçiler** için tasarlanmıştır. Kasten ayrıntılı ve bazen karmaşıktır. Amacı, yazılımın iç işleyişini ortaya çıkarmak ve beklenmeyen durumlarda içgörü sağlamaktır.

Gelecek bir güncelleme, **drone'dan doğrudan alınan günlükleri** de içerecek ve operatör ile otonom sistem arasındaki görünürlük döngüsünü tamamlayacaktır.

---

## Beyin: DroneClient ve Bağlantı Yaşam Döngüsü

Uygulamanın kalbinde `DroneClient` bulunur—bu PySide `QObject` alt sınıfı, ön uç GUI ile drone'un arka uç yığını arasındaki iletişimi düzenlemek üzere tasarlanmıştır.

Bu istemci, eşzamansız, sürekli ve drone ile etkileşime giren her şeyden sorumludur. Şu rolleri üstlenir:

- **ZMQ istemcisini başlatır**, komut gönderimi ve telemetri alımı sağlar.
    
- **Periyodik olarak durum güncellemeleri alır**, GPS koordinatları, yükseklik, pil durumu vb. bilgileri içerir.
    
- `takeoff`, `land`, `arm`, `rtl` gibi **görev kontrol komutlarını** Mavlink üzerinden iletir.
    
- **Vinç sistemini kontrol eder**, `pick_load`, `drop_load`, `raise_hook`, `drop_hook` gibi özel komutları ZMQ üzerinden drone'un mekanik alt sistemlerine iletir.
    
- **Drone'un kamerasından ham ve işlenmiş video akışı sağlar**.
    
    - Bunlar, `"raw"` ve `"processed"` gibi etiketlerle çok parçalı ZMQ mesajları olarak gönderilir ve yüksek performanslı bir arka plan thread'inde çözülür.
        

Bu mantığı `DroneClient` içinde soyutlayarak, durum yönetimi ve eşzamansız karmaşıklık UI'dan izole edilir, böylece kod okunabilirliği ve sorumluluk ayrımı korunur.

Daha derine inmek isteyen geliştiriciler, [`app.py`](https://github.com/amar-jay/nebula/blob/bf2a9aa755fe62006d5832af80da4bcd62566999/src/new_control_station/app.py#L82){target="_blank" rel="noopener noreferrer"} dosyasından DroneClient yaşam döngüsünün nasıl başlatıldığını ve ana uygulama penceresiyle nasıl entegre edildiğini inceleyebilir.

---

## Sistem Genel Bakış Şeması

Her şeyin nasıl bir araya geldiğini görmek için basitleştirilmiş bir sistem akış şeması:

![GCS Sistem Genel Bakış](../../assets/img/gcs-flow.svg)

Bu şema, Yer Kontrol İstasyonu, drone'un arka uç sistemleri ve Nebula 2025 mimarisini oluşturan bileşenler arasındaki etkileşimi gösterir. Verilerin drone'dan GCS'ye nasıl aktığını ve gerçek zamanlı kontrol ile izlemeye nasıl olanak sağladığını vurgular.

---

## Sonraki Adımlar

Bu dokümantasyon, Nebula Yer Kontrol İstasyonu'nun **kullanıcı arayüzü ve istemci yapısını** kapsar. Drone-yer iletişim yığını hakkında daha derin bir anlayış için [`/comms/`](/comms/) dizinine başvurabilirsiniz. Burada, **ZMQClient**'ın detaylı uygulamaları, serileştirme stratejileri ve bu arayüzün hava donanımıyla entegrasyonunu sağlayan destek modülleri bulunur.