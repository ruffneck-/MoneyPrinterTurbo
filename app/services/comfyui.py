import json
import os
from typing import Dict, List, Optional
import requests
from loguru import logger

from app.models.schema import MaterialInfo, VideoAspect
from app.utils import utils

class ComfyUIService:
    def __init__(self, host: str = "http://127.0.0.1:8188"):
        self.host = host
        self.api_base = f"{host}/api"

    def _get_workflow_json(self, workflow_path: str) -> Dict:
        """Load workflow JSON from file"""
        with open(workflow_path, 'r') as f:
            return json.load(f)
            
    def _queue_prompt(self, workflow: Dict) -> Dict:
        """Queue a prompt for execution"""
        url = f"{self.api_base}/queue"
        response = requests.post(url, json={"prompt": workflow})
        return response.json()

    def _get_history(self, prompt_id: str) -> Dict:
        """Get history for a prompt"""
        url = f"{self.api_base}/history/{prompt_id}"
        response = requests.get(url)
        return response.json()

    def _get_image(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """Get generated image data"""
        url = f"{self.api_base}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        response = requests.get(url, params=params)
        return response.content

    def generate_video(self, 
                      prompt: str,
                      video_aspect: VideoAspect,
                      frames: int = 24,
                      output_dir: str = "") -> Optional[str]:
        """Generate video using ComfyUI
        
        Args:
            prompt: Text prompt for video generation
            video_aspect: Target video aspect ratio
            frames: Number of frames to generate
            output_dir: Directory to save the output video
            
        Returns:
            Path to generated video file or None if failed
        """
        try:
            # Load default animation workflow
            workflow_path = os.path.join(
                utils.root_dir(),
                "resource",
                "workflows",
                "default_animation.json"
            )
            workflow = self._get_workflow_json(workflow_path)

            # Set parameters based on aspect ratio
            width, height = video_aspect.to_resolution()
            
            # Update workflow parameters
            # Note: Node IDs and parameters need to match your workflow
            workflow["1"]["inputs"]["text"] = prompt
            workflow["2"]["inputs"]["width"] = width
            workflow["2"]["inputs"]["height"] = height
            workflow["3"]["inputs"]["frames"] = frames

            # Queue the prompt
            queue_response = self._queue_prompt(workflow)
            prompt_id = queue_response["prompt_id"]
            
            # Wait for completion and get results
            while True:
                history = self._get_history(prompt_id)
                if prompt_id in history:
                    outputs = history[prompt_id]["outputs"]
                    break

            # Get the output video path
            # Note: This assumes the workflow outputs a video file
            # You'll need to adjust based on your workflow structure
            video_filename = outputs["4"]["images"][0]["filename"]
            video_subfolder = outputs["4"]["images"][0]["subfolder"]

            # Save video to output directory
            if output_dir:
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    
                video_data = self._get_image(video_filename, video_subfolder, "output")
                output_path = os.path.join(output_dir, video_filename)
                
                with open(output_path, "wb") as f:
                    f.write(video_data)
                    
                return output_path

        except Exception as e:
            logger.error(f"ComfyUI video generation failed: {str(e)}")
            return None