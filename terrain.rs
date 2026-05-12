//! terrain.rs — High-performance Terrain room engine for CPU systems.
//! Parses MUD room data, renders scenes, runs the calibration core.
//! Zero dependencies beyond std (except reqwest for HTTP).

use std::collections::HashMap;

/// A MUD room parsed into a visual scene.
#[derive(Debug, Clone)]
pub struct Scene {
    pub room: String,
    pub description: String,
    pub exits: Vec<(String, String)>,
    pub objects: Vec<String>,
    pub agents: Vec<String>,
}

impl Scene {
    /// Parse raw JSON room data from the MUD into a Scene.
    pub fn from_mud(data: &str) -> Result<Self, String> {
        let v: serde_json::Value = serde_json::from_str(data).map_err(|e| e.to_string())?;
        Ok(Scene {
            room: v["room"].as_str().unwrap_or("unknown").to_string(),
            description: v["description"].as_str().unwrap_or("").to_string(),
            exits: v["exits"].as_object()
                .map(|o| o.iter().map(|(k, v)| (k.clone(), v.as_str().unwrap_or("").to_string())).collect())
                .unwrap_or_default(),
            objects: v["objects"].as_array()
                .map(|a| a.iter().filter_map(|o| o["name"].as_str().map(String::from)).collect())
                .unwrap_or_default(),
            agents: v["agents_here"].as_array()
                .map(|a| a.iter().filter_map(|o| o.as_str().map(String::from)).collect())
                .unwrap_or_default(),
        })
    }
    
    /// Theme color for the room (matches terrain.html theming).
    pub fn theme(&self) -> (&'static str, &'static str, &'static str) {
        match self.room.as_str() {
            "harbor"   => ("#1a2a3a", "#2a4a6a", "#ffd700"),
            "forge"    => ("#2a1a0a", "#4a2a0a", "#ff6644"),
            "dojo"     => ("#1a1a2a", "#2a2a4a", "#44ff88"),
            "arena"    => ("#2a0a0a", "#4a1a1a", "#ff4444"),
            "archives" => ("#1a1a1a", "#2a2a2a", "#44aaff"),
            "tide-pool"=> ("#0a1a2a", "#1a3a5a", "#44ffaa"),
            _          => ("#0a0a1a", "#1a1a3a", "#ffd700"),
        }
    }
    
    /// Number of exits (doorways the player can walk through).
    pub fn exit_count(&self) -> usize { self.exits.len() }
    
    /// Number of interactable objects in the scene.
    pub fn object_count(&self) -> usize { self.objects.len() }
}

/// Fast scene cache: stores parsed scenes to avoid re-fetching.
pub struct SceneCache {
    scenes: HashMap<String, Scene>,
    max_entries: usize,
}

impl SceneCache {
    pub fn new(max: usize) -> Self {
        SceneCache { scenes: HashMap::new(), max_entries: max }
    }
    
    pub fn get(&self, room: &str) -> Option<&Scene> {
        self.scenes.get(room)
    }
    
    pub fn insert(&mut self, room: String, scene: Scene) {
        if self.scenes.len() >= self.max_entries {
            self.scenes.clear();  // Simple eviction
        }
        self.scenes.insert(room, scene);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_parse_harbor() {
        let data = r#"{"room":"harbor","description":"A bustling harbor.","exits":{"north":"forge"},"objects":[{"name":"anchor"}],"agents_here":["oracle1"]}"#;
        let scene = Scene::from_mud(data).unwrap();
        assert_eq!(scene.room, "harbor");
        assert_eq!(scene.exit_count(), 1);
        assert_eq!(scene.object_count(), 1);
        assert_eq!(scene.agents.len(), 1);
    }
    
    #[test]
    fn test_theme() {
        let data = r#"{"room":"forge","description":"","exits":{},"objects":[],"agents_here":[]}"#;
        let scene = Scene::from_mud(data).unwrap();
        let (_, _, accent) = scene.theme();
        assert_eq!(accent, "#ff6644");
    }
    
    #[test]
    fn test_cache() {
        let mut cache = SceneCache::new(2);
        let s1 = Scene { room: "harbor".into(), description: "".into(), exits: vec![], objects: vec![], agents: vec![] };
        let s2 = Scene { room: "forge".into(), description: "".into(), exits: vec![], objects: vec![], agents: vec![] };
        cache.insert("harbor".into(), s1);
        cache.insert("forge".into(), s2);
        assert!(cache.get("harbor").is_some());
        assert!(cache.get("forge").is_some());
    }
}
