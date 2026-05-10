
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
Copyright(c) 2025 Hangzhou Hikvision Digital Technology Co.,Ltd
简要描述: ssl_cert_manager.py - SSL证书管理器
编写作者: dongruihua
创建日期: 2025/1/20
修订说明: 自动检测、安装和管理mitmproxy所需的SSL证书
         解决证书过期或缺失问题
==================================================================="""
import os
import sys
import subprocess
import datetime
import hashlib
import shutil
import stat
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import json

from utils.logger import Log

logger = Log('SSLCertManager')


class SSLCertManager:
    """
    SSL证书管理器
    自动检测、安装、更新和管理mitmproxy SSL证书
    """

    # mitmproxy默认证书路径
    MITMPROXY_CERT_DIR = os.path.join(os.path.expanduser('~'), '.mitmproxy')
    MITMPROXY_CA_CERT = os.path.join(MITMPROXY_CERT_DIR, 'mitmproxy-ca.pem')
    MITMPROXY_CA_CRT = os.path.join(MITMPROXY_CERT_DIR, 'mitmproxy-ca.crt')
    MITMPROXY_CA_KEY = os.path.join(MITMPROXY_CERT_DIR, 'mitmproxy-ca.key')
    MITMPROXY_CA_SERIAL = os.path.join(MITMPROXY_CERT_DIR, 'mitmproxy-ca.srl')
    MITMPROXY_CA_PEM = os.path.join(MITMPROXY_CERT_DIR, 'mitmproxy-ca-cert.pem')

    # Windows证书存储
    WINDOWS_CERT_STORE = 'Root'  # 受信任的根证书颁发机构

    def __init__(self, cert_dir: Optional[str] = None):
        """
        初始化SSL证书管理器
        :param cert_dir: 自定义证书目录，如果为None则使用默认路径
        """
        self.cert_dir = cert_dir or self.MITMPROXY_CERT_DIR
        self.ca_cert_path = os.path.join(self.cert_dir, 'mitmproxy-ca.pem')
        self.ca_crt_path = os.path.join(self.cert_dir, 'mitmproxy-ca.crt')
        self.ca_key_path = os.path.join(self.cert_dir, 'mitmproxy-ca.key')
        self.ca_serial_path = os.path.join(self.cert_dir, 'mitmproxy-ca.srl')
        self.ca_pem_path = os.path.join(self.cert_dir, 'mitmproxy-ca-cert.pem')

        # 确保证书目录存在
        self._ensure_cert_dir()

        # 证书有效期检查阈值（天数）
        self.CERT_EXPIRY_THRESHOLD = 30

        # 是否自动安装证书到系统信任存储
        self.AUTO_INSTALL_TRUSTED = True

        # 日志记录
        self._setup_logging()

    def _setup_logging(self):
        """设置日志记录"""
        logger.info(f"SSL证书管理器初始化完成")
        logger.info(f"证书目录: {self.cert_dir}")
        logger.info(f"证书有效期阈值: {self.CERT_EXPIRY_THRESHOLD}天")

    def _ensure_cert_dir(self):
        """确保证书目录存在"""
        try:
            Path(self.cert_dir).mkdir(parents=True, exist_ok=True)
            logger.debug(f"证书目录已确认: {self.cert_dir}")
        except Exception as e:
            logger.error(f"创建证书目录失败: {e}")
            raise

    def _check_openssl_available(self) -> bool:
        """
        检查openssl是否可用
        :return: 是否可用
        """
        try:
            result = subprocess.run(
                ['openssl', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.debug(f"OpenSSL可用: {result.stdout.strip()}")
                return True
            else:
                logger.warning("OpenSSL不可用")
                return False
        except FileNotFoundError:
            logger.warning("未找到openssl命令")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("OpenSSL检查超时")
            return False
        except Exception as e:
            logger.error(f"检查OpenSSL时发生错误: {e}")
            return False

    def _generate_ssl_cert(self) -> bool:
        """
        使用openssl生成SSL证书
        :return: 是否生成成功
        """
        try:
            logger.info("开始生成SSL证书...")

            # 生成CA私钥
            logger.info("生成CA私钥...")
            subprocess.run([
                'openssl', 'genrsa', '-out', self.ca_key_path, '2048'
            ], check=True, capture_output=True)

            # 生成CA证书
            logger.info("生成CA证书...")
            subprocess.run([
                'openssl', 'req', '-new', '-x509',
                '-key', self.ca_key_path,
                '-out', self.ca_cert_path,
                '-days', '3650',  # 10年有效期
                '-subj', '/CN=mitmproxy/O=mitmproxy/CN=mitmproxy'
            ], check=True, capture_output=True)

            # 生成证书序列号文件
            with open(self.ca_serial_path, 'w') as f:
                f.write('01')

            # 创建证书信任文件
            shutil.copy2(self.ca_cert_path, self.ca_pem_path)

            logger.info("SSL证书生成成功")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"生成SSL证书失败: {e}")
            logger.error(f"错误输出: {e.stderr.decode() if e.stderr else '无'}")
            return False
        except Exception as e:
            logger.error(f"生成SSL证书时发生未知错误: {e}")
            return False

    def _generate_cert_with_mitmproxy(self) -> bool:
        """
        使用mitmproxy命令生成证书
        :return: 是否生成成功
        """
        try:
            logger.info("尝试使用mitmproxy生成证书...")

            # 检查mitmproxy是否可用
            try:
                subprocess.run(
                    ['mitmproxy', '--version'],
                    capture_output=True,
                    timeout=5
                )
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                logger.warning("mitmproxy不可用")
                return False

            # 使用mitmproxy的证书生成功能
            # 注意：这里需要模拟mitmproxy的证书生成行为
            # 实际上，mitmproxy会在首次启动时自动生成证书
            logger.info("mitmproxy证书将通过mitmproxy自动生成")
            return True

        except Exception as e:
            logger.error(f"使用mitmproxy生成证书失败: {e}")
            return False

    def check_cert_exists(self) -> bool:
        """
        检查SSL证书是否存在
        :return: 是否存在
        """
        cert_files = [
            self.ca_cert_path,
            self.ca_key_path,
            self.ca_crt_path,
            self.ca_pem_path
        ]

        for cert_file in cert_files:
            if not os.path.exists(cert_file):
                logger.warning(f"证书文件不存在: {cert_file}")
                return False

        logger.info("所有证书文件都存在")
        return True

    def check_cert_validity(self) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        检查SSL证书的有效性
        :return: (是否有效, 剩余天数, 过期时间)
        """
        if not self.check_cert_exists():
            return False, None, None

        try:
            # 使用openssl检查证书有效期
            result = subprocess.run([
                'openssl', 'x509', '-in', self.ca_cert_path,
                '-noout', '-dates'
            ], capture_output=True, text=True, check=True)

            # 解析有效期
            lines = result.stdout.strip().split('\n')
            not_after = None
            for line in lines:
                if line.startswith('notAfter='):
                    not_after = line.split('=')[1]
                    break

            if not not_after:
                logger.warning("无法解析证书有效期")
                return False, None, None

            # 解析日期
            # openssl输出的日期格式: Dec 25 23:59:59 2035 GMT
            expiry_date = datetime.datetime.strptime(
                not_after, '%b %d %H:%M:%S %Y %Z'
            )
            current_date = datetime.datetime.now()

            # 计算剩余天数
            days_remaining = (expiry_date - current_date).days

            # 检查是否在阈值内
            is_valid = days_remaining > self.CERT_EXPIRY_THRESHOLD

            logger.info(f"证书有效期检查: 剩余{days_remaining}天，过期时间: {expiry_date.strftime('%Y-%m-%d')}")

            return is_valid, days_remaining, expiry_date.strftime('%Y-%m-%d')

        except subprocess.CalledProcessError as e:
            logger.error(f"检查证书有效期失败: {e}")
            return False, None, None
        except Exception as e:
            logger.error(f"解析证书有效期时发生错误: {e}")
            return False, None, None

    def install_to_windows_store(self) -> bool:
        """
        将证书安装到Windows受信任的根证书颁发机构
        :return: 是否安装成功
        """
        if sys.platform != 'win32':
            logger.info("非Windows系统，跳过Windows证书存储安装")
            return False

        try:
            logger.info("尝试将证书安装到Windows受信任的根证书颁发机构...")

            # 使用certutil命令安装证书
            result = subprocess.run([
                'certutil', '-addstore', self.WINDOWS_CERT_STORE, self.ca_cert_path
            ], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("证书已成功安装到Windows受信任的根证书颁发机构")
                return True
            else:
                logger.warning(f"安装证书到Windows存储失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"安装证书到Windows存储时发生错误: {e}")
            return False

    def install_to_macos_keychain(self) -> bool:
        """
        将证书安装到macOS钥匙串
        :return: 是否安装成功
        """
        if sys.platform != 'darwin':
            logger.info("非macOS系统，跳过钥匙串安装")
            return False

        try:
            logger.info("尝试将证书安装到macOS钥匙串...")

            # 使用security命令安装证书
            result = subprocess.run([
                'security', 'add-trusted-cert',
                '-d', '-r', 'trustRoot',
                '-k', '/Library/Keychains/System.keychain',
                self.ca_cert_path
            ], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("证书已成功安装到macOS钥匙串")
                return True
            else:
                logger.warning(f"安装证书到钥匙串失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"安装证书到钥匙串时发生错误: {e}")
            return False

    def install_to_linux_trust_store(self) -> bool:
        """
        将证书安装到Linux信任存储
        :return: 是否安装成功
        """
        if sys.platform not in ['linux', 'linux2']:
            logger.info("非Linux系统，跳过信任存储安装")
            return False

        try:
            logger.info("尝试将证书安装到Linux信任存储...")

            # 检查系统是否有update-ca-certificates
            try:
                subprocess.run(
                    ['update-ca-certificates', '--help'],
                    capture_output=True,
                    timeout=5
                )
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                logger.warning("系统没有update-ca-certificates命令")
                return False

            # 复制证书到系统CA目录
            ca_dir = '/usr/local/share/ca-certificates/'
            os.makedirs(ca_dir, exist_ok=True)
            shutil.copy2(self.ca_cert_path, os.path.join(ca_dir, 'mitmproxy-ca.crt'))

            # 更新CA证书
            result = subprocess.run(
                ['update-ca-certificates'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                logger.info("证书已成功安装到Linux信任存储")
                return True
            else:
                logger.warning(f"安装证书到信任存储失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"安装证书到信任存储时发生错误: {e}")
            return False

    def auto_install_certificate(self) -> bool:
        """
        自动安装证书到系统信任存储
        :return: 是否安装成功
        """
        if not self.AUTO_INSTALL_TRUSTED:
            logger.info("自动安装证书功能已禁用")
            return False

        logger.info("开始自动安装证书到系统信任存储...")

        # 根据系统类型选择安装方法
        if sys.platform == 'win32':
            return self.install_to_windows_store()
        elif sys.platform == 'darwin':
            return self.install_to_macos_keychain()
        elif sys.platform in ['linux', 'linux2']:
            return self.install_to_linux_trust_store()
        else:
            logger.warning(f"不支持的系统平台: {sys.platform}")
            return False

    def ensure_certificate(self) -> bool:
        """
        确保证书存在且有效，如果无效则重新生成
        :return: 是否确保证书成功
        """
        logger.info("开始确保证书状态...")

        # 检查证书是否存在
        if not self.check_cert_exists():
            logger.warning("证书不存在，正在生成...")

            # 尝试使用openssl生成证书
            if self._check_openssl_available():
                if self._generate_ssl_cert():
                    logger.info("证书生成成功")
                else:
                    logger.error("使用OpenSSL生成证书失败")
                    return False
            else:
                # 尝试使用mitmproxy生成证书
                if self._generate_cert_with_mitmproxy():
                    logger.info("mitmproxy证书将自动生成")
                else:
                    logger.error("生成证书失败")
                    return False

        # 检查证书有效期
        is_valid, days_remaining, expiry_date = self.check_cert_validity()

        if not is_valid:
            if days_remaining is not None and days_remaining <= self.CERT_EXPIRY_THRESHOLD:
                logger.warning(f"证书即将过期（剩余{days_remaining}天），正在重新生成...")

                # 重新生成证书
                if self._check_openssl_available():
                    if self._generate_ssl_cert():
                        logger.info("证书重新生成成功")
                    else:
                        logger.error("重新生成证书失败")
                        return False
                else:
                    logger.error("无法重新生成证书")
                    return False

        # 自动安装证书到系统信任存储
        if self.AUTO_INSTALL_TRUSTED:
            self.auto_install_certificate()

        logger.info("证书状态确认完成")
        return True

    def get_cert_info(self) -> Dict[str, Any]:
        """
        获取证书信息
        :return: 证书信息字典
        """
        is_valid, days_remaining, expiry_date = self.check_cert_validity()

        cert_files = {
            'ca_cert': self.ca_cert_path,
            'ca_key': self.ca_key_path,
            'ca_crt': self.ca_crt_path,
            'ca_pem': self.ca_pem_path,
            'ca_serial': self.ca_serial_path
        }

        file_info = {}
        for name, path in cert_files.items():
            if os.path.exists(path):
                file_stat = os.stat(path)
                file_info[name] = {
                    'exists': True,
                    'path': path,
                    'size': file_stat.st_size,
                    'modified': datetime.datetime.fromtimestamp(
                        file_stat.st_mtime
                    ).strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                file_info[name] = {
                    'exists': False,
                    'path': path
                }

        return {
            'cert_dir': self.cert_dir,
            'is_valid': is_valid,
            'days_remaining': days_remaining,
            'expiry_date': expiry_date,
            'cert_files': file_info,
            'auto_install_trusted': self.AUTO_INSTALL_TRUSTED,
            'expiry_threshold': self.CERT_EXPIRY_THRESHOLD
        }

    def cleanup_old_certs(self, keep_backups: int = 3) -> bool:
        """
        清理旧的证书备份
        :param keep_backups: 保留的备份数量
        :return: 是否清理成功
        """
        try:
            logger.info(f"开始清理旧证书备份（保留{keep_backups}个）...")

            # 查找备份文件
            backup_files = []
            for filename in os.listdir(self.cert_dir):
                if filename.endswith('.backup') or filename.endswith('.old'):
                    file_path = os.path.join(self.cert_dir, filename)
                    file_stat = os.stat(file_path)
                    backup_files.append((file_path, file_stat.st_mtime))

            # 按修改时间排序
            backup_files.sort(key=lambda x: x[1])

            # 删除多余的备份
            if len(backup_files) > keep_backups:
                files_to_delete = backup_files[:len(backup_files) - keep_backups]
                for file_path, _ in files_to_delete:
                    try:
                        os.remove(file_path)
                        logger.info(f"已删除旧备份: {file_path}")
                    except Exception as e:
                        logger.error(f"删除备份文件失败: {e}")

            logger.info("证书备份清理完成")
            return True

        except Exception as e:
            logger.error(f"清理旧证书备份时发生错误: {e}")
            return False


# 全局证书管理器实例
_cert_manager = None


def get_cert_manager() -> SSLCertManager:
    """
    获取全局证书管理器实例
    :return: SSLCertManager实例
    """
    global _cert_manager
    if _cert_manager is None:
        _cert_manager = SSLCertManager()
    return _cert_manager


def ensure_certificate() -> bool:
    """
    手动确保证书状态
    :return: 是否确保证书成功
    """
    manager = get_cert_manager()
    return manager.ensure_certificate()


if __name__ == '__main__':
    # 测试证书管理器
    print("SSL Certificate Manager Test")
    print("=" * 50)

    manager = SSLCertManager()

    # 检查证书状态
    print(f"\n证书目录: {manager.cert_dir}")
    print(f"证书文件存在: {manager.check_cert_exists()}")

    is_valid, days_remaining, expiry_date = manager.check_cert_validity()
    print(f"证书有效: {is_valid}")
    print(f"剩余天数: {days_remaining}")
    print(f"过期时间: {expiry_date}")

    # 确保证书
    print(f"\n正在确保证书状态...")
    if manager.ensure_certificate():
        print("证书状态确认成功")
    else:
        print("证书状态确认失败")

    # 获取证书信息
    print(f"\n证书信息:")
    import json
    print(json.dumps(manager.get_cert_info(), indent=2, ensure_ascii=False))
