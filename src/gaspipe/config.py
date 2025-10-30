#!/usr/bin/env python3
"""
Configuration Management
========================

Centralized configuration for all pipeline components

UPDATED: Added export optimization settings for direct RealityCapture export
         to images folder, avoiding unnecessary file copying
"""

import json
from pathlib import Path
import tkinter as tk

class Config:
    """Central configuration manager"""
    
    def __init__(self):
        self.settings = {
            # Software paths - TUTTI CONFIGURABILI
            'software': {
                'ffmpeg': 'ffmpeg',
                'reality_capture': 'C:/Program Files/Epic Games/RealityScan_2.0/RealityScan.exe',
                'postshot': 'C:/Program Files/Jawset Postshot/bin/postshot-cli.exe',
                'rc_settings': 'C:/Users/Public/Documents/Capturing Reality/RealityCapture'
            },
            
            # Video processing settings - COMPLETI
            'video': {
                'fps': 1.0,
                'resolution': '4K (3840x1920)',  # 8K, 4K, 2K, FullHD, Custom
                'custom_width': 3840,
                'frames_format': 'PNG',  # PNG, JPG
                'frames_quality': 'high'  # high, medium, low
            },
            
            # Cubemap settings - COMPLETI
            'cubemap': {
                'size': '1920x1920',  # 1920x1920, 960x960
                'format': 'PNG',      # PNG, JPG
                'quality': 'high'     # high, medium, low
            },
            
            # PostShot settings - COMPLETI
            'postshot': {
                'profile': 'Splat MCMC',  # Splat MCMC, Splat Standard
                'trainsteps': 25          # Training steps in thousands
            },
            
            # Timeout e robustezza
            'processing': {
                'timeout_minutes': 15,    # Timeout per ogni processo
                'retry_failed': True      # Retry automatico
            },
            
            # Export settings - NUOVO per ottimizzazione export
            'export_settings': {
                'direct_export_to_images': True,  # RC esporta direttamente nella cartella immagini
                'ply_format': 'binary',           # binary o ascii (binary = più efficiente)
                'auto_create_xml': True,          # Crea automaticamente XML se non esistono
                'verify_pose_distribution': True  # Verifica che le pose non siano tutte in linea
            }
        }
        
        # Load saved config if exists
        self.config_file = Path.home() / '.gaspipe_config.json'
        self.load()
    
    def get_resolution(self):
        """Get width/height for video processing"""
        resolution_str = self.settings['video']['resolution']
        
        if resolution_str == 'Custom':
            width = self.settings['video']['custom_width']
        elif '8K' in resolution_str or '7680' in resolution_str:
            width = 7680
        elif '4K' in resolution_str or '3840' in resolution_str:
            width = 3840
        elif '2K' in resolution_str or '2048' in resolution_str:
            width = 2048
        elif 'FullHD' in resolution_str or '1920' in resolution_str:
            width = 1920
        else:
            width = 3840  # Default to 4K
            
        height = width // 2  # 2:1 aspect ratio for equirectangular
        return width, height
    
    def get_cubemap_size(self):
        """Get cubemap dimensions from size string"""
        size_str = self.settings['cubemap']['size']
        if 'x' in size_str:
            width = int(size_str.split('x')[0])
            return width
        return 1920  # Default
    
    def get_quality_value(self, quality_str):
        """Convert quality string to FFmpeg parameter"""
        quality_map = {
            'high': '2',
            'medium': '5',
            'low': '8'
        }
        return quality_map.get(quality_str.lower(), '2')
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def load(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved = json.load(f)
                    self.settings.update(saved)
            except Exception as e:
                print(f"Failed to load config: {e}")
    
    def get(self, category, key=None):
        """Get configuration value"""
        if key is None:
            return self.settings.get(category, {})
        return self.settings.get(category, {}).get(key)
    
    def set(self, category, key, value):
        """Set configuration value"""
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
        self.save()
    
    def get_export_settings(self):
        """Get export optimization settings"""
        return self.settings.get('export_settings', {
            'direct_export_to_images': True,
            'ply_format': 'binary',
            'auto_create_xml': True,
            'verify_pose_distribution': True
        })
    
    def is_direct_export_enabled(self):
        """Check if direct export to images folder is enabled"""
        return self.get_export_settings().get('direct_export_to_images', True)
    
    def get_ply_format(self):
        """Get PLY export format (binary or ascii)"""
        return self.get_export_settings().get('ply_format', 'binary')
    
    def should_create_xml_settings(self):
        """Check if XML settings should be created automatically"""
        return self.get_export_settings().get('auto_create_xml', True)