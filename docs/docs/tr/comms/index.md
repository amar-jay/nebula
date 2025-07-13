---
title: İletişim Mimarisi
description: Nebula Drone'un iletişim mimarisi, gerçek zamanlı drone kontrolü ve telemetri için ZeroMQ, asyncio ve PySide6 kullanımını detaylandırır.

date: 2025-07-13

author: amarjay

---

# İletişim Mimarisi

## Tarihçe

Drone (üzerinde bir kenar bilgisayar - Orin Nano bulunan) ile yer kontrol istasyonu arasında güvenilir bir iletişim kanalı tasarlamak, **Nebula 2025** projesinin Teknofest 2025 için geliştirilmesindeki en kritik - ve başlangıçta en sinir bozucu - zorluklardan biri oldu.

### Neden ROS Değil?

İlk bakışta, robotik iletişimi için doğal seçim [ROS](https://www.ros.org/) veya [ROS2](https://docs.ros.org/en/rolling/index.html) gibi görünebilir, özellikle de mesaj geçişi, görselleştirme, araçlar ve standart mesajlaşma protokolleri ekosistemi göz önüne alındığında. Ancak bilinçli bir şekilde bunları kullanmamaya karar verdik.

Ana sorun, ROS'un kendi kapalı ekosistemiyle aşırı entegre olmasından kaynaklanıyor. Cartographer, RViz veya rosbag gibi araçlar bu ortamda harika çalışıyor ancak dışarıda kötü bir şekilde sürdürülüyor. ROS1 için oluşturulmuş birçok açık kaynak paket, yeni Python veya sistem kütüphaneleriyle uyumsuz ve genellikle eski bağımlılıklar veya eksik içe aktarma yolları nedeniyle bozuluyor. Buna ek olarak, kontrol sistemleri veya görüntü işleme hatları için ROS'tan bağımsız köprüler oluşturmak - özellikle de zaman kısıtlamaları altında - bir bakım kabusuydu.

ROS2 ise daha modern olmasına rağmen ek karmaşıklık getirdi. Artık doğrudan TCP veya UDP soketleri kullanmıyor, bunun yerine **DDS** (Data Distribution Service) üzerine inşa ediliyor - bu da hata ayıklamak veya optimize etmek istemediğimiz çok daha ağır, kurumsal seviyede bir taşıma katmanı. Sıkı geliştirme döngülerimiz ve gömülü projemizin doğası göz önüne alındığında, daha hafif, daha hızlı uygulanabilir ve mantığını kurmanın daha kolay olduğu bir şeye ihtiyacımız vardı.

### Alternatifimiz: ZeroMQ

ROS'a güvenmek yerine, kendi mesaj geçiş mimarimizi **Python** ile sıfırdan geliştirdik ve iletişim omurgası olarak [ZeroMQ (ZMQ)](https://zeromq.org/) kullandık.

ZMQ mükemmel bir uyum sağladı: hafif, esnek ve soket türlerini anladıktan sonra son derece sezgisel. Ham soketlerin karmaşıklığını gizliyor ve dağıtık sistemler için sağlam desenler sunuyor: **Push/Pull**, **Request/Reply** ve nihayetinde üzerinde karar kıldığımız **Publisher/Subscriber**.

İlk denememizde Push-Pull modelini kullandık, bu teoride yer istasyonu ve drone arasındaki tek üretici/tek tüketici ilişkisi göz önüne alındığında işe yaradı. Ancak pratikte kırılgandı. Mesajlar çok hızlı gelirse veya bir taraf yeniden başlatılırsa, pull tarafı tıkanabiliyor veya senkronizasyonu kaybedebiliyordu. **Pub-Sub** modeline geçtik, bu daha iyi ayrışma, yerleşik konu filtreleme ve yeniden başlamalara karşı dayanıklılık sunuyordu. [The ZeroMQ Guide](https://zguide.zeromq.org/docs/chapter1/)'daki örneklerden ilham alarak, video kareleri, komut mesajları ve telemetri için kendi konu tabanlı kanallarımızı uyguladık.

![Pub-Sub Mimarisi](../../assets/img/comms-zmq-flow.svg)

### Mesaj Formatı

Basit tutmaya karar verdik. Protobuf yok. Özel serileştiriciler yok. Tüm mesajlar UTF-8 kodlanmış dizgiler olarak iletilir. Abone tarafında, uygun yerlerde Python'un yerleşik ayırıcı split fonksiyonunu kullanarak ayrıştırıyoruz. Bu bize katı bir şemaya kilitlenmeden hızlı bir şekilde yineleme yapma esnekliği sağladı.

### Sunucu Eşzamanlılık Evrimi

Kenar sunucusunda (drone üzerinde), sistemimizin ilk sürümü eşzamanlılık için geleneksel Python iş parçacıklarını kullanıyordu - her mesaj kanalını veya sensör akışını ayrı bir iş parçacığında ele alıyordu. Bu çalışsa da, hızla yönetilmesi zor hale geldi ve özellikle kapanışlar sırasında veya belirli soketler kesintiye uğradığında ince hatalara yatkın hale geldi.

Sonunda, **asyncio**'yu daha derinlemesine inceledikten ve biraz da ChatGPT'nin yardımıyla 😄, sunucuyu asenkron bir modele taşıdık. Şaşırtıcı bir şekilde, büyük performans kazanımları elde etmedik - ancak elde ettiğimiz şey **netlik** oldu. Kod okunması ve sürdürülmesi çarpıcı biçimde kolaylaştı. Mesaj kuyruklarını ve periyodik döngüleri yöneten eş yordamlar sayesinde, CPU zamanlaması ve durum geçişleri üzerinde çok daha hassas kontrol elde ettik. Bu yeni yapı ayrıca görüntü işleme gibi CPU yoğun görevleri bir `ThreadPoolExecutor` içinde izole etmeyi kolaylaştırdı ve daha önce sık sık takılmalara neden olan olay döngüsünün tıkanmasını önledi.

### İstemci Tarafı: PySide ve QThreads

İstemci tarafında (yani yer istasyonu), uygulama **PySide** (Python için Qt) ile oluşturulmuştur ve bu da kendi iş parçacığı modelini getirir. Başlangıçta, video akışlarını almak ve çözmek için düz Python iş parçacıkları kullandık, ancak bu Qt olay döngüsüyle çakıştı ve UI donmalarına veya yarış koşullarına neden oldu.

Bunu çözmek için ZMQ istemcimizi, ana GUI iş parçacığına güvenli bir şekilde sinyal gönderebilen bir `QThread` alt sınıfına taşıdık. Drone'dan gelen video kareleri bir ZMQ abone soketi üzerinden alınır, OpenCV ile çözülür ve Qt sinyalleri aracılığıyla ana UI'ye iletilir. Gelen her mesaj konusuna göre kategorize edilir: ham video, işlenmiş video, telemetri vb.

Aşağıda, `ZMQClient` içindeki gerçek uygulamadan bir alıntı bulunmaktadır:

```python
class ZMQVideoThread(QThread):
    def run(self):
        while self.running:
            try:
                if self.video_socket.poll(timeout=100) != 0:
                    topic, frame_data = self.video_socket.recv_multipart()

                    jpg_buffer = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = cv2.imdecode(jpg_buffer, cv2.IMREAD_COLOR)

                    if frame is not None:
                        if topic == b"processed_video":
                            self.processed_frame_received.emit(frame)
                        elif topic == b"video":
                            self.frame_received.emit(frame)
            except Exception:
                ...
```

Bu mimari, uçuşlar sırasında güvenilir olmuştur ve düşen kareler veya kilitlenmeler olmadan hem kontrol komutlarını hem de yüksek bant genişlikli video akışını desteklemektedir.

---

### Özet

- **Taşıma Katmanı**: [ZeroMQ](https://zeromq.org/), **Pub-Sub** modeli
    
- **Sunucu (Kenar Bilgisayar)**: Tüm eşzamanlılık için `asyncio`; görüntü işleme için `ThreadPoolExecutor` kullanır
    
- **İstemci (Yer İstasyonu)**: ZMQ soket işleme için `QThread`, GUI'ye PySide sinyalleri ile bağlı
    
- **Mesaj Formatı**: Dizgiler ve JSON
    

---

## Genel İletişim Mimarisi

Aşağıdaki diyagram, Nebula Drone'un iletişim sisteminin üst düzey yapısını göstermektedir. Hem drone'un kenar sunucusunda hem de GUI istemcisinde eşzamanlılık ve asenkronluğun nasıl ele alındığını vurgular.

![İletişim Mimarisi](../../assets/img/comms_.svg)

---

## Asenkron Kare İşleme

**`AsyncFrameProcessor`**'ımız, nesne tespitinin canlı video akışını asla kesmemesini sağlar. `start()` çağrıldığında, küçük bir giriş kuyruğunu izleyen bir daemon çalışan iş parçacığı başlatır. Gelen her `FrameData`, bir `ThreadPoolExecutor`'a (varsayılan olarak 2 iş parçacığı/çalışan) gönderilir ve duyarlılığı korumak için 500 ms içinde tamamlanmalıdır. İşlendikten sonra, sonuçlar ikinci bir kuyruğa girer; eğer bu dolarsa, en eski sonucu atarız böylece yalnızca taze kareler yayılır.

`_process_frame` içinde şunları yaparız:

1. Dünya koordinatlarında nesneleri tespit etmek ve konumlandırmak için YOLO takipçimizi çağırırız.    
2. `write_on_frame` ile açıklamaları ekleriz, herhangi bir hata oluşursa orijinal kareye zarif bir şekilde geri döneriz.

`submit_frame()` yöntemimiz, giriş kuyruğu dolduğunda kareleri atar ve sınırsız bellek büyümesini önler. Bu arada, `get_result()`, video döngüsünün engellemeden en son `ProcessedResult`'u almasını sağlar.

---

## MAVLink Proxy—Seri ve TCP Köprüsü

**`MAVLinkProxy`** sınıfı, MAVLink ile seri veya UDP üzerinden konuşmanın karmaşıklığını gizlerken bu akışı birden çok TCP istemcisiyle paylaşır. `start()` çağrıldığında şunları yaparız:

- Donanım için `/dev/ttyUSB0` veya simülasyon için `udp:` arasında seçim yaparak `ArdupilotConnection`'ı örnekleriz.
    
- Seçilen portta bir TCP sunucu soketi başlatırız.
    
- Gelen bağlantıları kabul etmek için bir iş parçacığı başlatırız - her biri gelen baytları MAVLink master'ına ileten kendi işleyici iş parçacığında - ve bir diğer iş parçacığı da MAVLink mesajlarını okuyarak tüm bağlı istemcilere yayınlar.
    

`get_drone_data()` yöntemimiz, GPS, duruş, yer seviyesi ve uçuş modunu tek bir demet içinde paketler. Herhangi bir başarısızlıkta bir uyarı günlüğe kaydeder ve `None` döndürür, böylece çağıran isteğe bağlı işlemeyi atlayabilir ve çökmeyi önler.

`stop()` çağrıldığında, sunucu soketini, tüm istemci soketlerini ve temel MAVLink bağlantısını temiz bir şekilde kapatırız, böylece hiçbir başıboş iş parçacığı veya soket kalmaz.

---

## ZMQServer—Video Yayınlama ve Komut İşleme

**`ZMQServer`**'ımız, ZeroMQ üzerinde iki eşzamanlı döngüyü yönetir: biri PUB soketi üzerinden ham ve işlenmiş video kareleri yayınlar, diğeri REP soketi üzerinden kontrol komutlarına yanıt verir.

### Başlatma & Takipçi Kurulumu

Kurucuda, portları, video kaynağını ve simülasyonda olup olmadığımızı kaydederiz. Hemen `_initialize_tracker()`'ı çağırırız ve burada şunları yaparız:

- Kamera içsel parametrelerini (Gazebo'dan veya görev tanımlarımızdan) alırız.
    
- Bu parametreler ve eğitilmiş modelimizle `YoloObjectTracker`'ı örnekleriz.
    
- Tespit işini boşaltmak için bir `AsyncFrameProcessor` oluştururuz.
    

Bu adımlardan herhangi biri başarısız olursa, bozuk bir takipçiyle çalışmamak için bir istisna fırlatırız.

### Video Yakalama & Kodlama

Akış başlamadan önce, `_initialize_video_capture()` Gazebo beslemesini veya canlı bir kamera cihazını açmaya çalışır. Başarısızlık günlüğe bir hata kaydeder ve döngüyü sonlandırır.

`_encode_frame()`'de, her kareyi OpenCV kullanarak JPEG'e sıkıştırırız. En verimli codec olmadığını kabul etmemize rağmen, JPEG istemci tarafında doğrudan `QImage` ile entegre olur ve zaman kısıtlamalarımız altında doğru dengeyi sağladı.

### Yayıncı Döngüsü

`async` `_video_publisher_loop`'umuz her yinelemede şunları yapar:

1. Yakalama kaynağından bir kare okuruz.
    
2. Hemen ham kareyi `video_socket.send_multipart` ile yayınlarız.
    
3. Her üçüncü karede, `MAVLinkProxy`'den en son drone verilerini alır ve `FrameData` içine sararız.
    
4. Bu kareyi `AsyncFrameProcessor`'a göndeririz. Kuyruğu doluysa günlüğe kaydeder ve atarız.
    
5. `results_queue`'yu herhangi bir `ProcessedResult` için tararız. Bulunursa, dahili GPS/piksel önbelleklerimizi günceller ve işlenmiş kareyi `"processed_"` altında yayınlarız.
    
6. Her beş saniyede bir, performansı izlememize yardımcı olmak için FPS'imizi günlüğe kaydederiz.
    
7. CPU'yu aşırı yüklememek için kısa bir süre uyuruz (`await asyncio.sleep(0.5)`).
    

Yakalama cihazı başarısız olursa, günlüğe kaydeder ve kısa bir aradan sonra yeniden deneriz. Çıkışta, yakalamayı serbest bırakır ve yayının durduğunu günlüğe kaydederiz.

### Kontrol Döngüsü

Eşzamanlı olarak, `_control_receiver_loop` REP soketimizde komut dizgilerini dinler. Bir mesaj geldiğinde, bilinen konulara karşı şerit ve karşılaştırırız:

- **Load/Hook komutları** dahili bir `hook_state`'i günceller, idempotence'a göre ACK veya NACK verir.
    
- **STATUS** mevcut kanca durumunu döndürür.
    
- **HELIPAD_GPS** ve **TANK_GPS** en son koordinatlarımız varsa onlarla yanıt verir.
    

Her başarılı komut günlüğe kaydedilir; bilinmeyen komutlar "NACK: Bilinmeyen komut." ile yanıtlanır.

### Yaşam Döngüsü Yönetimi

`start()` çağrıldığında, PUB ve REP soketlerimizi bağlarız, kare işlemcisini başlatırız, `running = True` yaparız ve her iki döngüyü de `asyncio.gather` ile başlatırız. Ardından gelen bir `stop()` bayrağı temizler, işlemciyi durdurur, soketleri kapatır ve ZeroMQ bağlamını sonlandırır.

Bu, bu sunucunun tam yaşam döngüsü yönetimidir, böylece başıboş iş parçacıkları veya soketler bırakmadan temiz bir şekilde başlatılabilir ve durdurulabilir.

![Yaşam Döngüsü Yönetimi](../../assets/img/comms-async-flow.svg)