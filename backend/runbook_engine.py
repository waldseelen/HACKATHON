"""
LogSense AI – Automated Runbook Engine
========================================
Generates context-aware recovery playbooks based on detected cascade
failure patterns and signals. Each runbook is a structured, step-by-step
recovery plan tailored to the specific failure mode.

Runbook Features:
  • Phased recovery (Emergency Stop → Cleanup → Restart → Monitor)
  • Conditional action matrix
  • Verification checkpoints
  • Rollback triggers
  • Estimated time-to-recovery
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from cascade_detector import CascadeDetectionResult, SignalType

logger = logging.getLogger("logsense.runbook")


# ── Runbook Data Structures ──────────────────────────────

@dataclass
class RunbookStep:
    """A single step in a recovery runbook."""
    order: int
    title: str
    description: str
    commands: list[str]
    phase: str  # PHASE_1 through PHASE_4
    estimated_minutes: int = 2
    requires_confirmation: bool = False
    rollback_command: Optional[str] = None
    verification: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "order": self.order,
            "title": self.title,
            "description": self.description,
            "commands": self.commands,
            "phase": self.phase,
            "estimated_minutes": self.estimated_minutes,
            "requires_confirmation": self.requires_confirmation,
        }
        if self.rollback_command:
            d["rollback_command"] = self.rollback_command
        if self.verification:
            d["verification"] = self.verification
        return d


@dataclass
class Runbook:
    """Complete recovery runbook for a cascade failure."""
    id: str
    title: str
    severity: str
    description: str
    cascade_type: str
    detected_signals: list[str]
    estimated_recovery_minutes: int
    steps: list[RunbookStep]
    conditional_actions: list[dict]
    rollback_triggers: list[str]
    monitoring_commands: list[str]
    post_mortem_checklist: list[str]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "cascade_type": self.cascade_type,
            "detected_signals": self.detected_signals,
            "estimated_recovery_minutes": self.estimated_recovery_minutes,
            "steps": [s.to_dict() for s in self.steps],
            "conditional_actions": self.conditional_actions,
            "rollback_triggers": self.rollback_triggers,
            "monitoring_commands": self.monitoring_commands,
            "post_mortem_checklist": self.post_mortem_checklist,
            "total_steps": len(self.steps),
            "phases": list(set(s.phase for s in self.steps)),
        }


# ── Runbook Templates ────────────────────────────────────

class RunbookEngine:
    """Generates recovery runbooks based on cascade detection results."""

    def generate(self, detection: CascadeDetectionResult) -> Optional[Runbook]:
        """Generate a runbook from cascade detection result."""
        if not detection.is_cascade:
            return None

        runbook_id = detection.runbook_id
        generator = self._GENERATORS.get(runbook_id)

        if not generator:
            logger.warning(f"No runbook template for: {runbook_id}")
            return self._generic_runbook(detection)

        return generator(self, detection)

    # ── OOM Kill Loop ─────────────────────────────────────

    def _oom_kill_loop(self, det: CascadeDetectionResult) -> Runbook:
        steps = [
            RunbookStep(
                order=1,
                title="Trafik Kesimi - Yeni Request Durdur",
                description="OOM döngüsünden çıkmak için önce trafiği kes. "
                            "Mevcut bağlantılar timeout ile kapansın.",
                commands=[
                    "kubectl scale deployment <app> --replicas=0 --namespace=prod",
                    "# veya: nginx upstream'i down olarak işaretle",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
                verification="kubectl get pods -n prod | grep <app> → 0 running",
            ),
            RunbookStep(
                order=2,
                title="Unhealthy Pod'ları Temizle",
                description="CrashLoopBackOff ve OOMKilled pod'ları force delete ile temizle.",
                commands=[
                    "kubectl delete pod <pod-name> --force --grace-period=0",
                    "kubectl get pods -n prod | grep -E 'OOMKilled|CrashLoop|Error'",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=3,
                title="Memory Limit 2x Artır",
                description="Resource quota ve deployment memory limitlerini geçici olarak 2 katına çıkar.",
                commands=[
                    "kubectl set resources deployment <app> --limits=memory=2Gi --requests=memory=1Gi -n prod",
                    "# veya: kubectl edit resourcequota -n prod → memory.limit 2x yap",
                ],
                phase="PHASE_2",
                estimated_minutes=2,
                requires_confirmation=True,
                rollback_command="kubectl set resources deployment <app> --limits=memory=1Gi --requests=memory=512Mi -n prod",
            ),
            RunbookStep(
                order=4,
                title="Heap Dump Analizi (JVM/Node.js varsa)",
                description="Memory leak tespit etmek için heap dump oluştur ve GC tuning yap.",
                commands=[
                    "# JVM: jmap -dump:format=b,file=/tmp/heap.hprof <pid>",
                    "# Node: node --heapsnapshot-signal=SIGUSR2 → kill -SIGUSR2 <pid>",
                    "# GC Tuning: -XX:MaxRAMPercentage=75 -XX:+UseG1GC",
                    "# Node: --max-old-space-size=768 (limit'in %75'i)",
                ],
                phase="PHASE_2",
                estimated_minutes=3,
            ),
            RunbookStep(
                order=5,
                title="Servisi Kademeli Başlat",
                description="Memory limitleri artırıldıktan sonra 50% kapasite ile başla. "
                            "3 dakika izle, OOM yoksa tam kapasiteye çık.",
                commands=[
                    "kubectl scale deployment <app> --replicas=2 -n prod  # 50% kapasite",
                    "kubectl top pods -n prod -l app=<app>  # Memory izle",
                    "# 3dk OOM yoksa:",
                    "kubectl scale deployment <app> --replicas=4 -n prod  # Tam kapasite",
                ],
                phase="PHASE_3",
                estimated_minutes=5,
                verification="kubectl get pods -l app=<app> → 0 restarts, memory < %75",
            ),
            RunbookStep(
                order=6,
                title="Memory Alert Eşiğini Düşür",
                description="Erken uyarı için Prometheus alert eşiğini %70'e düşür.",
                commands=[
                    "# Prometheus alert rule: memory_usage > 70% (eski: 85%)",
                    "# Grafana dashboard memory panel'ini güncelle",
                ],
                phase="PHASE_4",
                estimated_minutes=2,
            ),
        ]

        return Runbook(
            id="oom_kill_loop",
            title="🔴 OOM Kill Loop Recovery",
            severity=det.severity,
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=14,
            steps=steps,
            conditional_actions=[
                {"condition": "3dk içinde OOM tekrarı", "action": "Full rollback + traffic external failover"},
                {"condition": "GC overhead > %50", "action": "Heap dump + GC tuning (JVM: G1GC, Node: max-old-space-size)"},
                {"condition": "Memory leak doğrulandı", "action": "Hotfix deploy + canary release"},
            ],
            rollback_triggers=[
                "3dk içinde OOM tekrarı",
                "Memory kullanımı %95 üzeri kalıyor",
                "Pod restart sayısı > 3",
            ],
            monitoring_commands=[
                "watch -n 30 'kubectl top pods -n prod -l app=<app>'",
                "kubectl logs -f deployment/<app> -n prod | grep -i 'oom\\|killed\\|memory'",
            ],
            post_mortem_checklist=[
                "Memory leak root cause belirlendi mi?",
                "Resource limits production profiling ile güncellendi mi?",
                "Alert eşikleri düzeltildi mi?",
                "Load test ile yeni limitler doğrulandı mı?",
            ],
        )

    # ── Database Cascade ──────────────────────────────────

    def _database_cascade(self, det: CascadeDetectionResult) -> Runbook:
        steps = [
            RunbookStep(
                order=1,
                title="Idle DB Bağlantılarını Sonlandır",
                description="5 dakikadan eski idle bağlantıları temizle. Connection pool'u flush'la.",
                commands=[
                    "kubectl exec -it <postgres-pod> -- psql -c \"SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE state='idle' AND state_change < NOW() - INTERVAL '5 minutes';\"",
                    "kubectl exec -it <postgres-pod> -- psql -c \"SELECT count(*) FROM pg_stat_activity;\"",
                ],
                phase="PHASE_1",
                estimated_minutes=2,
                verification="Active connections < max_connections * 0.8",
            ),
            RunbookStep(
                order=2,
                title="Connection Pool Boyutunu Artır",
                description="PostgreSQL max_connections ve uygulama pool size'ı artır.",
                commands=[
                    "# PostgreSQL: ALTER SYSTEM SET max_connections = 200; SELECT pg_reload_conf();",
                    "# App config: pool_size=100, max_overflow=50, pool_timeout=30",
                    "# PgBouncer kullanılıyorsa: max_client_conn=200, default_pool_size=50",
                ],
                phase="PHASE_2",
                estimated_minutes=3,
                requires_confirmation=True,
                rollback_command="ALTER SYSTEM SET max_connections = 100; SELECT pg_reload_conf();",
            ),
            RunbookStep(
                order=3,
                title="Health Check ile DB Erişim Doğrula",
                description="PostgreSQL health check endpoint'ini kontrol et.",
                commands=[
                    "kubectl exec -it <postgres-pod> -- pg_isready -h localhost -p 5432",
                    "curl -f http://<postgres-service>:5432/health || echo 'DB UNREACHABLE'",
                    "kubectl exec -it <postgres-pod> -- psql -c 'SELECT 1 AS health_check;'",
                ],
                phase="PHASE_2",
                estimated_minutes=1,
                verification="pg_isready returns 'accepting connections'",
            ),
            RunbookStep(
                order=4,
                title="DB-Bağımlı Servisleri Restart Et",
                description="Connection pool reset için uygulama pod'larını sıralı restart et.",
                commands=[
                    "kubectl rollout restart deployment/<app> -n prod",
                    "kubectl rollout status deployment/<app> -n prod --timeout=120s",
                ],
                phase="PHASE_3",
                estimated_minutes=3,
                verification="kubectl get pods -l app=<app> → all Running, 0 restarts",
            ),
            RunbookStep(
                order=5,
                title="Connection Leak Tespiti",
                description="Bağlantı leak'i var mı kontrol et. Idle connection sayısı sürekli artıyorsa leak var.",
                commands=[
                    "# Her 30sn'de connection count izle:",
                    "watch -n 30 \"kubectl exec -it <postgres-pod> -- psql -c "
                    "'SELECT state, count(*) FROM pg_stat_activity GROUP BY state;'\"",
                    "# Application-side: connection pool metrics endpoint kontrol et",
                ],
                phase="PHASE_4",
                estimated_minutes=5,
            ),
        ]

        return Runbook(
            id="database_cascade",
            title="🔴 Database Cascade Failure Recovery",
            severity=det.severity,
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=14,
            steps=steps,
            conditional_actions=[
                {"condition": "max_connections hâlâ yetersiz", "action": "PgBouncer/ProxySQL connection pooler ekle"},
                {"condition": "Connection leak doğrulandı", "action": "Hotfix: connection close/dispose ekle + deploy"},
                {"condition": "DB disk dolu", "action": "VACUUM FULL + eski verileri archive et"},
            ],
            rollback_triggers=[
                "5dk içinde connection count tekrar max'a ulaşırsa",
                "DB health check başarısız olursa",
                "Uygulama pod'ları CrashLoopBackOff'a girerse",
            ],
            monitoring_commands=[
                "watch -n 30 \"kubectl exec <postgres-pod> -- psql -c 'SELECT count(*), state FROM pg_stat_activity GROUP BY state;'\"",
                "kubectl logs -f deployment/<app> -n prod | grep -i 'connection\\|pool\\|timeout'",
            ],
            post_mortem_checklist=[
                "Connection leak root cause bulundu mu?",
                "Pool size production profiling ile belirlendi mi?",
                "Connection lifetime ve idle timeout ayarlandı mı?",
                "PgBouncer gibi connection pooler ihtiyacı var mı?",
            ],
        )

    # ── Disk Pressure ─────────────────────────────────────

    def _disk_pressure(self, det: CascadeDetectionResult) -> Runbook:
        steps = [
            RunbookStep(
                order=1,
                title="Disk Kullanımını Tespit Et",
                description="Hangi dizin/volume en çok yer kaplıyor belirle.",
                commands=[
                    "df -h /dev/sda1 /var/log /var/lib/docker",
                    "du -sh /var/log/* /var/lib/docker/* | sort -rh | head -20",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=2,
                title="Docker Temizlik",
                description="Kullanılmayan Docker image, container ve volume'ları sil.",
                commands=[
                    "docker system prune -af --volumes",
                    "docker image prune -af  # Dangling images",
                    "docker volume prune -f  # Orphan volumes",
                ],
                phase="PHASE_2",
                estimated_minutes=3,
                verification="df -h → disk usage < %80",
            ),
            RunbookStep(
                order=3,
                title="Log Temizlik + Rotation",
                description="Eski logları temizle ve logrotate yapılandır.",
                commands=[
                    "journalctl --vacuum-time=2d  # Journal 2 günden eski sil",
                    "find /var/log -name '*.log' -mtime +7 -delete  # 7 günden eski loglar",
                    "find /var/log -name '*.gz' -mtime +3 -delete  # Eski compressed loglar",
                    "# Kalıcı: logrotate config ekle:",
                    "# /etc/logrotate.d/application → daily, rotate 7, compress, maxsize 100M",
                ],
                phase="PHASE_2",
                estimated_minutes=2,
            ),
            RunbookStep(
                order=4,
                title="File Descriptor Limiti Artır",
                description="Eğer 'too many open files' hatası da varsa ulimit'i artır.",
                commands=[
                    "ulimit -n 65536  # Geçici (mevcut session)",
                    "echo '* soft nofile 65536' >> /etc/security/limits.conf  # Kalıcı",
                    "echo '* hard nofile 65536' >> /etc/security/limits.conf",
                    "# Kontrol: cat /proc/<pid>/limits | grep 'open files'",
                ],
                phase="PHASE_2",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=5,
                title="Disk Alert Eşiğini Düşür (%80)",
                description="Erken uyarı için disk alert eşiğini %80'e düşür.",
                commands=[
                    "# Prometheus: disk_usage_percent > 80 (eski: 95)",
                    "# Node Exporter: node_filesystem_avail_bytes monitoring",
                ],
                phase="PHASE_4",
                estimated_minutes=1,
            ),
        ]

        return Runbook(
            id="disk_pressure",
            title="🔴 Disk Pressure Crisis Recovery",
            severity=det.severity,
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=8,
            steps=steps,
            conditional_actions=[
                {"condition": "Disk hâlâ %95+", "action": "Node drain + yeni node provision et"},
                {"condition": "Docker overlay2 şişmiş", "action": "docker system prune + storage driver kontrol"},
                {"condition": "DB WAL dosyaları büyümüş", "action": "pg_archivecleanup + checkpoint_segments ayarla"},
            ],
            rollback_triggers=[
                "5dk içinde disk yine %95 dolarsa",
                "Servisler write failure vermeye devam ederse",
            ],
            monitoring_commands=[
                "watch -n 30 'df -h /dev/sda1 && du -sh /var/log /var/lib/docker'",
            ],
            post_mortem_checklist=[
                "Log rotation düzgün çalışıyor mu?",
                "Disk kapasitesi yeterli mi, uzun vade artış gerekli mi?",
                "Monitoring alert eşikleri düzeltildi mi?",
                "Geçici dosya temizleme cron job'ı eklendi mi?",
            ],
        )

    # ── Network / TLS Cascade ─────────────────────────────

    def _network_tls_cascade(self, det: CascadeDetectionResult) -> Runbook:
        steps = [
            RunbookStep(
                order=1,
                title="SSL Sertifika Durumunu Kontrol Et",
                description="Sertifika süresi dolmuş mu, ne zaman doluyor kontrol et.",
                commands=[
                    "openssl s_client -connect <domain>:443 -servername <domain> 2>/dev/null | "
                    "openssl x509 -noout -dates",
                    "# Kubernetes Secret kontrol:",
                    "kubectl get secret <tls-secret> -n prod -o jsonpath='{.data.tls\\.crt}' | "
                    "base64 -d | openssl x509 -noout -dates",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=2,
                title="Sertifika Yenile",
                description="Let's Encrypt veya manual sertifika yenileme.",
                commands=[
                    "certbot renew --force-renewal",
                    "# veya manual cert ile Kubernetes secret güncelle:",
                    "kubectl create secret tls <secret-name> --cert=cert.pem --key=key.pem "
                    "--dry-run=client -o yaml | kubectl apply -f -",
                    "# cert-manager varsa:",
                    "kubectl delete certificate <cert-name> -n prod  # Recreate trigger",
                ],
                phase="PHASE_2",
                estimated_minutes=3,
                requires_confirmation=True,
                verification="openssl s_client -connect <domain>:443 → notAfter > now + 30 days",
            ),
            RunbookStep(
                order=3,
                title="Nginx / Ingress Reload",
                description="Yeni sertifikayı yüklemek için ingress controller'ı reload et.",
                commands=[
                    "kubectl rollout restart deployment/nginx-ingress-controller -n ingress-nginx",
                    "# veya bare metal nginx: nginx -s reload",
                    "# Ingress annotation güncellemesi ile de tetiklenebilir",
                ],
                phase="PHASE_3",
                estimated_minutes=2,
                verification="curl -vI https://<domain> 2>&1 | grep 'SSL connection'",
            ),
            RunbookStep(
                order=4,
                title="Upstream Servis Durumunu Doğrula",
                description="Backend servislerinin upstream olarak erişilebilir olduğunu doğrula.",
                commands=[
                    "curl -f http://<backend-service>:<port>/health",
                    "kubectl get endpoints <service-name> -n prod",
                    "# Nginx upstream check:",
                    "kubectl logs deployment/nginx -n ingress-nginx --tail=20 | grep upstream",
                ],
                phase="PHASE_3",
                estimated_minutes=2,
            ),
            RunbookStep(
                order=5,
                title="Trafik Kademeli Aç",
                description="SSL düzeldikten sonra trafiği kademeli aç, 503 yoksa tam aç.",
                commands=[
                    "# Rate limit ile başla:",
                    "kubectl annotate ingress <app> nginx.ingress.kubernetes.io/rate-limit='10' --overwrite",
                    "# 2dk izle, 503 yoksa kaldır:",
                    "kubectl annotate ingress <app> nginx.ingress.kubernetes.io/rate-limit- --overwrite",
                ],
                phase="PHASE_3",
                estimated_minutes=3,
            ),
        ]

        return Runbook(
            id="network_tls_cascade",
            title="🔴 Network / TLS Cascade Recovery",
            severity=det.severity,
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=11,
            steps=steps,
            conditional_actions=[
                {"condition": "SSL handshake hâlâ fail", "action": "Sertifika chain eksik mi kontrol et (intermediate cert)"},
                {"condition": "Upstream 502 devam ediyor", "action": "Backend pod'ları restart + health check kontrol"},
                {"condition": "DNS propagation sorunu", "action": "DNS TTL düşür + alternatif DNS provider dene"},
            ],
            rollback_triggers=[
                "Yeni sertifika da başarısız olursa",
                "10dk içinde 503 oranı > %5",
            ],
            monitoring_commands=[
                "watch -n 30 'curl -sI https://<domain> | head -3 && kubectl get pods -n ingress-nginx'",
            ],
            post_mortem_checklist=[
                "Sertifika auto-renewal neden başarısız oldu?",
                "cert-manager veya certbot cronjob aktif mi?",
                "DNS validation token'ı güncel mi?",
                "Sertifika expiry alert'i var mı (30, 14, 7 gün önceden)?",
            ],
        )

    # ── Resource Exhaustion ───────────────────────────────

    def _resource_exhaustion(self, det: CascadeDetectionResult) -> Runbook:
        steps = [
            RunbookStep(
                order=1,
                title="File Descriptor ve Connection Durumunu Tespit Et",
                description="Hangi kaynaklar limitinde tespit et.",
                commands=[
                    "cat /proc/sys/fs/file-nr  # allocated / max",
                    "lsof | wc -l  # Total open files",
                    "ss -s  # Socket summary",
                    "kubectl exec <postgres-pod> -- psql -c 'SHOW max_connections;'",
                    "kubectl exec <postgres-pod> -- psql -c 'SELECT count(*) FROM pg_stat_activity;'",
                ],
                phase="PHASE_1",
                estimated_minutes=2,
            ),
            RunbookStep(
                order=2,
                title="File Descriptor Limiti Artır",
                description="Ulimit artır + systemd service limit güncelle.",
                commands=[
                    "ulimit -n 65536",
                    "echo '* soft nofile 65536' >> /etc/security/limits.conf",
                    "echo '* hard nofile 65536' >> /etc/security/limits.conf",
                    "# systemd service: LimitNOFILE=65536 ekle",
                    "systemctl daemon-reload && systemctl restart <service>",
                ],
                phase="PHASE_2",
                estimated_minutes=2,
            ),
            RunbookStep(
                order=3,
                title="Idle Bağlantıları Temizle",
                description="DB, Redis ve ağ bağlantılarında idle olanları sonlandır.",
                commands=[
                    "# PostgreSQL idle connections:",
                    "kubectl exec <postgres-pod> -- psql -c \"SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE state='idle' AND state_change < NOW() - INTERVAL '5 min';\"",
                    "# Redis connections: redis-cli CLIENT LIST | grep idle | wc -l",
                    "# TCP connections: ss -tnp state time-wait | wc -l",
                ],
                phase="PHASE_2",
                estimated_minutes=2,
            ),
            RunbookStep(
                order=4,
                title="Connection Pool + Timeout Ayarları",
                description="Bağlantı havuzu boyutlarını ve timeout'ları optimize et.",
                commands=[
                    "# DB: max_connections=200, idle_timeout=60s, connection_lifetime=30min",
                    "# Redis: maxclients 10000, timeout 300",
                    "# App: pool_size=50, pool_recycle=1800, pool_pre_ping=true",
                ],
                phase="PHASE_3",
                estimated_minutes=3,
                requires_confirmation=True,
            ),
        ]

        return Runbook(
            id="resource_exhaustion",
            title="🟠 Resource Exhaustion Storm Recovery",
            severity=det.severity,
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=9,
            steps=steps,
            conditional_actions=[
                {"condition": "Leak devam ediyor", "action": "lsof -p <pid> ile hangi dosyalar açık tespit et"},
                {"condition": "TCP TIME_WAIT çok fazla", "action": "net.ipv4.tcp_tw_reuse=1 kernel param"},
            ],
            rollback_triggers=[
                "5dk içinde file descriptor tekrar limit'e ulaşırsa",
                "Connection count sürekli artıyorsa (leak)",
            ],
            monitoring_commands=[
                "watch -n 30 'cat /proc/sys/fs/file-nr && ss -s | head -5'",
            ],
            post_mortem_checklist=[
                "File/socket leak root cause bulundu mu?",
                "Connection pool parametreleri optimize edildi mi?",
                "OS-level limit'ler kalıcı şekilde artırıldı mı?",
            ],
        )

    # ── Full Cascade ──────────────────────────────────────

    def _full_cascade(self, det: CascadeDetectionResult) -> Runbook:
        steps = [
            RunbookStep(
                order=1,
                title="⚠️ ACİL: Tüm Trafiği Kes",
                description="Cascade devam ediyor — önce kanamayı durdur. Tüm ingress trafiğini kes.",
                commands=[
                    "kubectl scale deployment <app> --replicas=0 --namespace=prod",
                    "# ALB/nginx: tüm upstream'leri down olarak işaretle",
                    "# WAF: emergency block rule aktif et",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
                verification="kubectl get pods -n prod | grep Running → 0",
            ),
            RunbookStep(
                order=2,
                title="OOM / Restart Döngüsünü Kır",
                description="Tüm CrashLoopBackOff ve OOMKilled pod'ları force delete.",
                commands=[
                    "kubectl get pods -n prod | grep -E 'OOMKilled|CrashLoop|Error' | "
                    "awk '{print $1}' | xargs kubectl delete pod --force --grace-period=0 -n prod",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=3,
                title="Resource Quota Geçici 2x Artır",
                description="Memory ve ephemeral storage limitlerini artır.",
                commands=[
                    "kubectl edit resourcequota -n prod",
                    "# memory.limit: 2x yap",
                    "# ephemeral-storage: 20Gi → 50Gi",
                ],
                phase="PHASE_1",
                estimated_minutes=2,
                requires_confirmation=True,
            ),
            RunbookStep(
                order=4,
                title="Disk + Docker Temizlik",
                description="Kullanılmayan kaynakları temizle, log rotation uygula.",
                commands=[
                    "docker system prune -af --volumes",
                    "journalctl --vacuum-time=2d",
                    "find /var/log -name '*.log' -mtime +7 -delete",
                    "du -sh /var/lib/docker /var/log | sort -rh",
                ],
                phase="PHASE_2",
                estimated_minutes=3,
                verification="df -h → disk < %80",
            ),
            RunbookStep(
                order=5,
                title="Connection Pool Flush + DB Temizlik",
                description="Idle DB bağlantılarını temizle, Redis cache flush.",
                commands=[
                    "kubectl exec -it <postgres-pod> -- psql -c \"SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE state='idle' AND state_change < NOW() - INTERVAL '5 min';\"",
                    "redis-cli FLUSHALL  # Sadece cache ise!",
                ],
                phase="PHASE_2",
                estimated_minutes=2,
            ),
            RunbookStep(
                order=6,
                title="File Descriptor Limiti Artır",
                description="Too many open files hatasını çöz.",
                commands=[
                    "ulimit -n 65536",
                    "echo '* soft nofile 65536' >> /etc/security/limits.conf",
                    "echo '* hard nofile 65536' >> /etc/security/limits.conf",
                ],
                phase="PHASE_2",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=7,
                title="SSL Sertifika Yenile (varsa expired)",
                description="SSL handshake fail varsa sertifikayı yenile.",
                commands=[
                    "certbot renew --force-renewal",
                    "kubectl create secret tls <secret> --cert=cert.pem --key=key.pem "
                    "--dry-run=client -o yaml | kubectl apply -f -",
                ],
                phase="PHASE_3",
                estimated_minutes=3,
                requires_confirmation=True,
            ),
            RunbookStep(
                order=8,
                title="Data Layer Servisleri Başlat (Sıralı)",
                description="Önce stateful servisler: PostgreSQL → Redis → Kafka. "
                            "Her birinin healthy olmasını bekle.",
                commands=[
                    "kubectl scale statefulset postgres --replicas=1 -n prod",
                    "kubectl wait --for=condition=ready pod/postgres-0 --timeout=120s -n prod",
                    "kubectl scale statefulset redis --replicas=1 -n prod",
                    "kubectl wait --for=condition=ready pod/redis-0 --timeout=60s -n prod",
                    "kubectl scale deployment kafka --replicas=3 -n prod",
                ],
                phase="PHASE_3",
                estimated_minutes=5,
                verification="All stateful pods Ready, health endpoints responding",
            ),
            RunbookStep(
                order=9,
                title="Health Check SONRA App Başlat (%50)",
                description="Data layer sağlıklıysa uygulamayı %50 kapasite ile başlat.",
                commands=[
                    "curl -f http://<postgres-service>:5432/health || exit 1",
                    "curl -f http://<redis-service>:6379/ping || exit 1",
                    "# Her şey OK ise:",
                    "kubectl scale deployment <app> --replicas=3 -n prod  # %50 kapasite",
                ],
                phase="PHASE_3",
                estimated_minutes=3,
                verification="kubectl get pods -l app=<app> → all Running, 0 restarts",
            ),
            RunbookStep(
                order=10,
                title="Trafik Kademeli Aç (Circuit Breaker ON)",
                description="Rate limit 10 req/s → 100 req/s → normal. Her adımda 2dk izle.",
                commands=[
                    "kubectl annotate ingress <app> nginx.ingress.kubernetes.io/rate-limit='10' --overwrite",
                    "# 2dk izle: 503/OOM yoksa rate limit artır",
                    "kubectl annotate ingress <app> nginx.ingress.kubernetes.io/rate-limit='100' --overwrite",
                    "# 2dk daha izle, sorun yoksa kaldır:",
                    "kubectl annotate ingress <app> nginx.ingress.kubernetes.io/rate-limit- --overwrite",
                ],
                phase="PHASE_3",
                estimated_minutes=6,
            ),
            RunbookStep(
                order=11,
                title="Monitoring + Alert Eşiği Güncelle",
                description="Yeni alert eşikleri: Memory %70, Disk %80, CPU %75.",
                commands=[
                    "# Prometheus alert rules güncelle:",
                    "# memory_usage > 70% (eski: 85%)",
                    "# disk_usage > 80% (eski: 95%)",
                    "# cpu_usage > 75% (eski: 90%)",
                    "# Pod restart = 0 hedefi",
                ],
                phase="PHASE_4",
                estimated_minutes=2,
            ),
            RunbookStep(
                order=12,
                title="Resource Limit Profiling",
                description="Production profiling ile optimal resource limit belirle. +50% buffer ekle.",
                commands=[
                    "kubectl set resources deployment <app> "
                    "--limits=memory=1Gi,cpu=1000m --requests=memory=512Mi,cpu=500m -n prod",
                    "# Circuit breaker config:",
                    "# timeout=3s, failure_threshold=50%, retry=3x exponential backoff",
                    "# DB pool: max_connections=100, idle_timeout=60s, connection_lifetime=30min",
                ],
                phase="PHASE_4",
                estimated_minutes=3,
            ),
        ]

        return Runbook(
            id="full_cascade",
            title="🔴 FULL PRODUCTION CASCADE RECOVERY",
            severity="critical",
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=32,
            steps=steps,
            conditional_actions=[
                {"condition": "disk > %95", "action": "Log rotation + docker prune (adım 4)"},
                {"condition": "OOMKilled loop", "action": "replicas=0 + memory limit 2x (adım 1,3)"},
                {"condition": "max_connections aşıldı", "action": "Idle terminate + pool resize (adım 5)"},
                {"condition": "503 cascade", "action": "Upstream isolate + bulkhead pattern (adım 1,10)"},
                {"condition": "SSL handshake fail", "action": "Cert renew + secret update (adım 7)"},
                {"condition": "GC overhead", "action": "Heap dump + GC tuning"},
            ],
            rollback_triggers=[
                "3dk içinde OOM tekrarı → Full rollback + traffic external failover",
                "5dk içinde disk yine %95 → Node drain + yeni node provision",
                "Error rate > %5 after 10dk → Previous deployment restore",
            ],
            monitoring_commands=[
                "watch -n 30 'kubectl top nodes && kubectl top pods -n prod && df -h /dev/sda1'",
                "# Hedef: CPU < %70, Memory < %75, Disk < %80, Pod restarts = 0",
            ],
            post_mortem_checklist=[
                "Cascade'in başlangıç noktası (root trigger) belirlendi mi?",
                "Hangi servis ilk fail etti?",
                "Alert'ler neden daha erken tetiklenmedi?",
                "Resource limit'ler production profiling ile güncellendi mi?",
                "Circuit breaker / bulkhead pattern eklendi mi?",
                "Incident response playbook güncel mi?",
                "Loadtest ile yeni konfigürasyon doğrulandı mı?",
            ],
        )

    # ── Messaging Infrastructure Down ─────────────────────

    def _messaging_down(self, det: CascadeDetectionResult) -> Runbook:
        steps = [
            RunbookStep(
                order=1,
                title="Redis / Kafka Erişim Kontrolü",
                description="Redis ve Kafka pod'larının çalışıp çalışmadığını kontrol et.",
                commands=[
                    "kubectl get pods -n prod -l app=redis",
                    "kubectl get pods -n prod -l app=kafka",
                    "redis-cli -h <redis-host> PING",
                    "kafka-broker-api-versions.sh --bootstrap-server <kafka-host>:9092",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=2,
                title="Redis Restart + Cache Rebuild",
                description="Redis pod'unu restart et, cache cold start'a hazırlan.",
                commands=[
                    "kubectl rollout restart statefulset/redis -n prod",
                    "kubectl wait --for=condition=ready pod/redis-0 -n prod --timeout=60s",
                    "redis-cli PING  # PONG dönmeli",
                    "# Cache warm-up: uygulamada cache priming endpoint varsa çağır",
                ],
                phase="PHASE_2",
                estimated_minutes=3,
                verification="redis-cli PING → PONG",
            ),
            RunbookStep(
                order=3,
                title="Kafka Broker'ları Başlat",
                description="Kafka broker'larını sıralı başlat, partition rebalance bekle.",
                commands=[
                    "kubectl scale statefulset kafka --replicas=3 -n prod",
                    "# Partition durumunu kontrol et:",
                    "kafka-topics.sh --describe --bootstrap-server <kafka>:9092 | grep -i 'under-replicated'",
                    "# Consumer group lag kontrol:",
                    "kafka-consumer-groups.sh --bootstrap-server <kafka>:9092 --list",
                ],
                phase="PHASE_2",
                estimated_minutes=5,
            ),
            RunbookStep(
                order=4,
                title="Async Servisler Restart",
                description="Mesajlaşma altyapısı sağlıklı olduktan sonra consumer servisleri restart et.",
                commands=[
                    "kubectl rollout restart deployment/<consumer-app> -n prod",
                    "# Consumer lag monitör et: lag azalmalı",
                ],
                phase="PHASE_3",
                estimated_minutes=3,
            ),
        ]

        return Runbook(
            id="messaging_down",
            title="🟠 Messaging Infrastructure Recovery",
            severity=det.severity,
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=12,
            steps=steps,
            conditional_actions=[
                {"condition": "Kafka partition corrupt", "action": "kafka-log-dirs.sh ile tespit + reassign"},
                {"condition": "Redis data loss kabul edilemez", "action": "AOF/RDB restore'dan başlat"},
            ],
            rollback_triggers=[
                "Redis/Kafka 5dk içinde tekrar çökerse",
                "Consumer lag artmaya devam ederse",
            ],
            monitoring_commands=[
                "watch -n 30 'redis-cli INFO memory | grep used_memory_human && "
                "kafka-consumer-groups.sh --describe --group <group> --bootstrap-server <kafka>:9092'",
            ],
            post_mortem_checklist=[
                "Redis/Kafka neden çöktü (OOM, disk, network)?",
                "Backpressure mekanizması var mı?",
                "Dead letter queue implementasyonu gerekli mi?",
            ],
        )

    # ── Upstream 503 Storm ────────────────────────────────

    def _upstream_storm(self, det: CascadeDetectionResult) -> Runbook:
        steps = [
            RunbookStep(
                order=1,
                title="Upstream Servis Durumunu Tespit Et",
                description="Hangi upstream'ler down? Nginx error log'ları kontrol et.",
                commands=[
                    "kubectl logs deployment/nginx-ingress-controller -n ingress-nginx --tail=50 "
                    "| grep -E 'upstream|502|503'",
                    "kubectl get endpoints -n prod  # Backend endpoint'leri var mı?",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=2,
                title="Rate Limiting Aktif Et",
                description="Client retry storm'u durdurmak için trafiği kıs.",
                commands=[
                    "kubectl annotate ingress <app> nginx.ingress.kubernetes.io/rate-limit='10' --overwrite",
                    "# veya nginx level: limit_req zone=one burst=5 nodelay;",
                ],
                phase="PHASE_1",
                estimated_minutes=1,
            ),
            RunbookStep(
                order=3,
                title="Backend Pod'ları Restart + Scale",
                description="Down olan backend servisleri restart et, gerekirse scale up.",
                commands=[
                    "kubectl rollout restart deployment/<backend-app> -n prod",
                    "kubectl rollout status deployment/<backend-app> --timeout=120s",
                    "kubectl scale deployment/<backend-app> --replicas=5 -n prod  # Scale up",
                ],
                phase="PHASE_2",
                estimated_minutes=3,
                verification="kubectl get pods -l app=<backend> → all Running",
            ),
            RunbookStep(
                order=4,
                title="Circuit Breaker + Bulkhead Pattern",
                description="Gelecekteki cascade'leri önlemek için circuit breaker ekle.",
                commands=[
                    "# Resilience4j / Istio circuit breaker:",
                    "# timeout: 3s, failure_threshold: 50%, recovery: 30s",
                    "# Bulkhead: max concurrent calls = 25 per service",
                    "# Retry: 3x exponential backoff (1s, 2s, 4s)",
                ],
                phase="PHASE_3",
                estimated_minutes=5,
                requires_confirmation=True,
            ),
        ]

        return Runbook(
            id="upstream_storm",
            title="🟠 Upstream 503 Storm Recovery",
            severity=det.severity,
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=10,
            steps=steps,
            conditional_actions=[
                {"condition": "Backend OOMKilled", "action": "Memory limit artır + OOM runbook uygula"},
                {"condition": "Retry storm devam", "action": "WAF ile aggressive rate limit"},
            ],
            rollback_triggers=[
                "10dk sonra error rate > %5",
                "Backend pod'ları tekrar fail ederse",
            ],
            monitoring_commands=[
                "watch -n 30 'kubectl logs deployment/nginx --tail=5 -n ingress-nginx | grep -c 503'",
            ],
            post_mortem_checklist=[
                "Upstream neden 503 verdi?",
                "Circuit breaker eklendi mi?",
                "Client-side retry politikası güncel mi?",
                "Graceful degradation stratejisi var mı?",
            ],
        )

    # ── Generic Fallback ──────────────────────────────────

    def _generic_runbook(self, det: CascadeDetectionResult) -> Runbook:
        """Fallback runbook for unrecognized cascade patterns."""
        steps = [
            RunbookStep(
                order=1,
                title="Durumu Değerlendir",
                description="Aktif sinyalleri incele ve etkilenen servisleri belirle.",
                commands=[
                    "kubectl get pods -n prod --field-selector=status.phase!=Running",
                    "kubectl top nodes",
                    "kubectl top pods -n prod",
                    "df -h",
                ],
                phase="PHASE_1",
                estimated_minutes=2,
            ),
            RunbookStep(
                order=2,
                title="Acil Müdahale",
                description="Sinyallere göre ilgili kaynakları temizle/restart et.",
                commands=[
                    "# Sinyaller: " + ", ".join(det.detected_signals),
                    "kubectl rollout restart deployment/<affected-app> -n prod",
                ],
                phase="PHASE_2",
                estimated_minutes=5,
            ),
            RunbookStep(
                order=3,
                title="Doğrulama ve İzleme",
                description="Servislerin sağlığını doğrula, 15dk izleme yap.",
                commands=[
                    "kubectl get pods -n prod",
                    "watch -n 30 'kubectl top pods -n prod'",
                ],
                phase="PHASE_3",
                estimated_minutes=5,
            ),
        ]

        return Runbook(
            id="generic",
            title=f"🟡 {det.cascade_type} Recovery",
            severity=det.severity,
            cascade_type=det.cascade_type,
            description=det.description,
            detected_signals=det.detected_signals,
            estimated_recovery_minutes=12,
            steps=steps,
            conditional_actions=[],
            rollback_triggers=["10dk içinde aynı hatalar tekrarlarsa"],
            monitoring_commands=["watch -n 30 'kubectl get pods -n prod && kubectl top nodes'"],
            post_mortem_checklist=["Root cause analizi yapıldı mı?", "Alert eşikleri güncellendi mi?"],
        )

    # ── Generator Registry ────────────────────────────────

    _GENERATORS = {
        "oom_kill_loop": _oom_kill_loop,
        "database_cascade": _database_cascade,
        "disk_pressure": _disk_pressure,
        "network_tls_cascade": _network_tls_cascade,
        "resource_exhaustion": _resource_exhaustion,
        "full_cascade": _full_cascade,
        "messaging_down": _messaging_down,
        "upstream_storm": _upstream_storm,
    }
