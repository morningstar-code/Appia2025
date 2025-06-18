from config.system_config import SystemConfig, GeneratedProject
from typing import Dict, List
import logging
import os
import time
import json
import shutil


class GeneratorAgent:
    """
    Advanced Generator Agent that creates exact website clones based on analysis data.
    Supports React, Next.js, Vue, Angular, and vanilla HTML/CSS/JS.
    """
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.project_templates = self._initialize_templates()
        self.component_generators = self._initialize_component_generators()
    
    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(self.__class__.__name__)
    
    def _initialize_templates(self) -> Dict:
        """Initialize project templates for different frameworks"""
        return {
            "react": self._get_react_template(),
            "next": self._get_nextjs_template(),
            "vue": self._get_vue_template(),
            "angular": self._get_angular_template(),
            "vanilla": self._get_vanilla_template()
        }
    
    def _initialize_component_generators(self) -> Dict:
        """Initialize component generators for different frameworks"""
        return {
            "react": self._generate_react_component,
            "next": self._generate_next_component,
            "vue": self._generate_vue_component,
            "angular": self._generate_angular_component,
            "vanilla": self._generate_vanilla_component
        }
    
    async def generate_code(self, analysis: Dict, target_framework: str = None) -> GeneratedProject:
        """
        Main method to generate complete website clone based on analysis
        """
        self.logger.info("Starting code generation process...")
        # Robust framework selection
        framework = "react"
        framework_dict = analysis.get("framework")
        if isinstance(framework_dict, dict):
            primary = framework_dict.get("primary")
            if isinstance(primary, str) and primary:
                framework = primary
        if not isinstance(framework, str) or not framework:
            framework = "react"
        self.logger.info(f"Target framework: {framework}")
        project_structure = {}
        config_files = {}
        # Ensure package_json is always present
        package_json = analysis.get("cloning_requirements", {}).get("package_json")
        if not isinstance(package_json, dict) or not package_json:
            package_json = self._generate_package_json({}, framework)
        assets = analysis.get("cloning_requirements", {}).get("assets", [])
        build_commands = analysis.get("cloning_requirements", {}).get("build_commands", [])
        dev_commands = analysis.get("cloning_requirements", {}).get("dev_commands", [])
        deployment_config = analysis.get("cloning_requirements", {}).get("deployment_config", {})

        # Dynamically create files/components as described by analysis
        component_files = analysis.get("cloning_requirements", {}).get("component_files", [])
        component_descriptions = analysis.get("components_description", {})
        for file_name in component_files:
            description = component_descriptions.get(file_name, "")
            project_structure[file_name] = await self._generate_real_code(file_name, description, framework, file_type="component")

        # Pages
        page_files = analysis.get("cloning_requirements", {}).get("pages", [])
        page_descriptions = analysis.get("pages_description", {})
        for file_name in page_files:
            description = page_descriptions.get(file_name, "")
            project_structure[file_name] = await self._generate_real_code(file_name, description, framework, file_type="page")

        # Styles
        style_files = analysis.get("cloning_requirements", {}).get("styles", [])
        style_descriptions = analysis.get("styles_description", {})
        for file_name in style_files:
            description = style_descriptions.get(file_name, "")
            project_structure[file_name] = await self._generate_real_code(file_name, description, framework, file_type="style")

        # Config files
        config_files = analysis.get("cloning_requirements", {}).get("config_files", {})

        # Fallback: Add minimal templates if missing
        if framework == "react":
            if not any(f for f in project_structure if f.lower().endswith("index.js") or f.lower().endswith("index.jsx")):
                project_structure["src/index.jsx"] = "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './index.css';\n\nReactDOM.createRoot(document.getElementById('root')).render(<App />);"
            if not any(f for f in project_structure if f.lower().endswith("app.js") or f.lower().endswith("app.jsx")):
                project_structure["src/App.jsx"] = "export default function App() {\n  return <div>Hello from App!</div>;\n}"
            if not any(f for f in project_structure if f.lower().endswith("index.html")):
                project_structure["public/index.html"] = "<!DOCTYPE html>\n<html lang='en'>\n  <head>\n    <meta charset='UTF-8' />\n    <meta name='viewport' content='width=device-width, initial-scale=1.0' />\n    <title>Cloned React App</title>\n  </head>\n  <body>\n    <div id='root'></div>\n  </body>\n</html>"
        elif framework == "next":
            if not any(f for f in project_structure if f.lower().endswith("_app.js") or f.lower().endswith("_app.jsx")):
                project_structure["pages/_app.js"] = "export default function MyApp({ Component, pageProps }) {\n  return <Component {...pageProps} />;\n}"
            if not any(f for f in project_structure if f.lower().endswith("index.js") or f.lower().endswith("index.jsx")):
                project_structure["pages/index.js"] = "export default function Home() {\n  return <div>Hello from Next.js Home!</div>;\n}"
        elif framework == "vue":
            if not any(f for f in project_structure if f.lower().endswith("main.js")):
                project_structure["src/main.js"] = "import { createApp } from 'vue';\nimport App from './App.vue';\ncreateApp(App).mount('#app');"
            if not any(f for f in project_structure if f.lower().endswith("app.vue")):
                project_structure["src/App.vue"] = "<template>\n  <div>Hello from Vue App!</div>\n</template>\n<script>\nexport default { name: 'App' }\n</script>"
            if not any(f for f in project_structure if f.lower().endswith("index.html")):
                project_structure["public/index.html"] = "<!DOCTYPE html>\n<html lang='en'>\n  <head>\n    <meta charset='UTF-8' />\n    <meta name='viewport' content='width=device-width, initial-scale=1.0' />
    <title>Cloned Vue App</title>\n  </head>\n  <body>\n    <div id='app'></div>\n  </body>\n</html>"
        elif framework == "vanilla":
            if not any(f for f in project_structure if f.lower().endswith("index.html")):
                project_structure["index.html"] = "<!DOCTYPE html>\n<html lang='en'>\n  <head>\n    <meta charset='UTF-8' />\n    <meta name='viewport' content='width=device-width, initial-scale=1.0' />\n    <title>Cloned Vanilla App</title>\n  </head>\n  <body>\n    <h1>Hello from Vanilla JS!</h1>\n    <script src='main.js'></script>\n  </body>\n</html>"
            if not any(f for f in project_structure if f.lower().endswith("main.js")):
                project_structure["main.js"] = "console.log('Hello from Vanilla JS!');"

        # Ensure .gitignore is always present
        if ".gitignore" not in config_files and ".gitignore" not in project_structure:
            config_files[".gitignore"] = self._generate_gitignore(framework)

        # Ensure README.md is always present
        if "README.md" not in config_files and "README.md" not in project_structure:
            config_files["README.md"] = self._generate_readme(framework)

        # Ensure package.json is always present in config_files
        if "package.json" not in config_files and package_json:
            config_files["package.json"] = json.dumps(package_json, indent=2)

        generated_project = GeneratedProject(
            framework=framework,
            project_structure=project_structure,
            package_json=package_json,
            config_files=config_files,
            assets=assets,
            build_commands=build_commands,
            dev_commands=dev_commands,
            deployment_config=deployment_config
        )

        # Save in a nested project folder inside cloned_sites
        await self._save_project(generated_project, subdir="project")
        self.logger.info("Code generation completed successfully")
        return generated_project

    async def _save_project(self, generated_project: GeneratedProject, subdir: str = "") -> None:
        import shutil
        timestamp = int(time.time())
        project_name = f"cloned_{generated_project.framework}_{timestamp}"
        base_dir = os.path.join(self.config.output_dir, project_name)
        output_dir = os.path.join(base_dir, subdir) if subdir else base_dir
        os.makedirs(output_dir, exist_ok=True)
        for file_path, content in generated_project.project_structure.items():
            abs_path = os.path.join(output_dir, file_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
        # Save package.json if present
        if generated_project.package_json:
            with open(os.path.join(output_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps(generated_project.package_json, indent=2))
        # Save config files if present
        for file_path, content in generated_project.config_files.items():
            abs_path = os.path.join(output_dir, file_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                if isinstance(content, dict):
                    f.write(json.dumps(content, indent=2))
                else:
                    f.write(str(content))
        self.logger.info(f"Project saved to {output_dir}")
    
    def _determine_framework(self, analysis: Dict, target_framework: str = None) -> str:
        """Determine the best framework for the project"""
        if target_framework:
            return target_framework.lower()
        
        detected_framework = analysis.get("framework", {}).get("primary", "unknown")
        
        # Framework mapping and fallbacks
        framework_map = {
            "react": "react",
            "next": "next",
            "nextjs": "next",
            "vue": "vue",
            "vuejs": "vue",
            "angular": "angular",
            "svelte": "svelte",
            "unknown": "react"  # Default fallback
        }
        
        return framework_map.get(detected_framework.lower(), "react")
    
    async def _generate_components(self, analysis: Dict, framework: str) -> Dict[str, str]:
        """Generate all components based on analysis"""
        components = {}
        component_list = analysis.get("components", [])
        
        self.logger.info(f"Generating {len(component_list)} components for {framework}")
        
        for component_name in component_list:
            component_code = await self._generate_single_component(
                component_name, analysis, framework
            )
            
            file_extension = self._get_file_extension(framework)
            file_path = f"components/{component_name.capitalize()}.{file_extension}"
            components[file_path] = component_code
        
        return components
    
    async def _generate_single_component(self, component_name: str, analysis: Dict, framework: str) -> str:
        """Generate a single component based on framework"""
        generator_func = self.component_generators.get(framework, self._generate_react_component)
        return await generator_func(component_name, analysis)
    
    async def _generate_react_component(self, component_name: str, analysis: Dict) -> str:
        """Generate React component"""
        colors = analysis.get("colors", {})
        typography = analysis.get("typography", {})
        interactive_elements = analysis.get("interactive_elements", {})
        
        # Component-specific logic
        if component_name.lower() == "header":
            return self._generate_react_header(analysis)
        elif component_name.lower() == "navigation":
            return self._generate_react_navigation(analysis)
        elif component_name.lower() == "hero":
            return self._generate_react_hero(analysis)
        elif component_name.lower() == "footer":
            return self._generate_react_footer(analysis)
        elif component_name.lower() == "cards":
            return self._generate_react_cards(analysis)
        elif component_name.lower() == "forms":
            return self._generate_react_forms(analysis)
        else:
            return self._generate_generic_react_component(component_name, analysis)
    
    def _generate_react_header(self, analysis: Dict) -> str:
        """Generate React Header component"""
        colors = analysis.get("colors", {})
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        
        if css_framework == "tailwind":
            return f'''import React, {{ useState }} from 'react';
import Navigation from './Navigation';

const Header = () => {{
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="bg-white shadow-md fixed w-full top-0 z-50">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="text-2xl font-bold text-gray-800">
              Your Logo
            </div>
          </div>
          
          <Navigation />
          
          <div className="md:hidden">
            <button
              onClick={{() => setIsMenuOpen(!isMenuOpen)}}
              className="text-gray-600 hover:text-gray-800 focus:outline-none"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={{2}} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
        
        {{isMenuOpen && (
          <div className="md:hidden mt-4 pb-4">
            <Navigation mobile={{true}} />
          </div>
        )}}
      </div>
    </header>
  );
}};

export default Header;'''
        else:
            return f'''import React, {{ useState }} from 'react';
import Navigation from './Navigation';
import './Header.css';

const Header = () => {{
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="header">
      <div className="header-container">
        <div className="header-content">
          <div className="logo">
            <div className="logo-text">Your Logo</div>
          </div>
          
          <Navigation />
          
          <div className="mobile-menu-button">
            <button
              onClick={{() => setIsMenuOpen(!isMenuOpen)}}
              className="menu-toggle"
            >
              ☰
            </button>
          </div>
        </div>
        
        {{isMenuOpen && (
          <div className="mobile-menu">
            <Navigation mobile={{true}} />
          </div>
        )}}
      </div>
    </header>
  );
}};

export default Header;'''
    
    def _generate_react_navigation(self, analysis: Dict) -> str:
        """Generate React Navigation component"""
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        
        if css_framework == "tailwind":
            return '''import React from 'react';
import { Link } from 'react-router-dom';

const Navigation = ({ mobile = false }) => {
  const navItems = [
    { name: 'Home', href: '/' },
    { name: 'About', href: '/about' },
    { name: 'Services', href: '/services' },
    { name: 'Contact', href: '/contact' },
  ];

  const baseClasses = mobile 
    ? "flex flex-col space-y-2" 
    : "hidden md:flex items-center space-x-8";

  const linkClasses = mobile
    ? "block py-2 px-4 text-gray-700 hover:bg-gray-100 rounded transition-colors"
    : "text-gray-700 hover:text-blue-600 transition-colors font-medium";

  return (
    <nav className={baseClasses}>
      {navItems.map((item) => (
        <Link
          key={item.name}
          to={item.href}
          className={linkClasses}
        >
          {item.name}
        </Link>
      ))}
    </nav>
  );
};

export default Navigation;'''
        else:
            return '''import React from 'react';
import { Link } from 'react-router-dom';
import './Navigation.css';

const Navigation = ({ mobile = false }) => {
  const navItems = [
    { name: 'Home', href: '/' },
    { name: 'About', href: '/about' },
    { name: 'Services', href: '/services' },
    { name: 'Contact', href: '/contact' },
  ];

  return (
    <nav className={`navigation ${mobile ? 'mobile' : 'desktop'}`}>
      {navItems.map((item) => (
        <Link
          key={item.name}
          to={item.href}
          className="nav-link"
        >
          {item.name}
        </Link>
      ))}
    </nav>
  );
};

export default Navigation;'''
    
    def _generate_react_hero(self, analysis: Dict) -> str:
        """Generate React Hero component"""
        colors = analysis.get("colors", {})
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        
        if css_framework == "tailwind":
            return f'''import React from 'react';

const Hero = () => {{
  return (
    <section className="bg-gradient-to-r from-blue-600 to-purple-700 text-white py-20 px-4 mt-16">
      <div className="container mx-auto text-center">
        <h1 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
          Welcome to Our Amazing Website
        </h1>
        <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto opacity-90">
          Discover innovative solutions that transform your business and drive success in the digital age.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors">
            Get Started
          </button>
          <button className="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-600 transition-colors">
            Learn More
          </button>
        </div>
      </div>
    </section>
  );
}};

export default Hero;'''
        else:
            return '''import React from 'react';
import './Hero.css';

const Hero = () => {
  return (
    <section className="hero">
      <div className="hero-container">
        <div className="hero-content">
          <h1 className="hero-title">
            Welcome to Our Amazing Website
          </h1>
          <p className="hero-subtitle">
            Discover innovative solutions that transform your business and drive success in the digital age.
          </p>
          <div className="hero-buttons">
            <button className="btn btn-primary">
              Get Started
            </button>
            <button className="btn btn-secondary">
              Learn More
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;'''
    
    def _generate_react_footer(self, analysis: Dict) -> str:
        """Generate React Footer component"""
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        
        if css_framework == "tailwind":
            return '''import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-gray-800 text-white py-12">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-xl font-bold mb-4">Company</h3>
            <ul className="space-y-2">
              <li><a href="/about" className="hover:text-gray-300 transition-colors">About Us</a></li>
              <li><a href="/careers" className="hover:text-gray-300 transition-colors">Careers</a></li>
              <li><a href="/news" className="hover:text-gray-300 transition-colors">News</a></li>
            </ul>
          </div>
          <div>
            <h3 className="text-xl font-bold mb-4">Services</h3>
            <ul className="space-y-2">
              <li><a href="/web-design" className="hover:text-gray-300 transition-colors">Web Design</a></li>
              <li><a href="/development" className="hover:text-gray-300 transition-colors">Development</a></li>
              <li><a href="/consulting" className="hover:text-gray-300 transition-colors">Consulting</a></li>
            </ul>
          </div>
          <div>
            <h3 className="text-xl font-bold mb-4">Support</h3>
            <ul className="space-y-2">
              <li><a href="/help" className="hover:text-gray-300 transition-colors">Help Center</a></li>
              <li><a href="/contact" className="hover:text-gray-300 transition-colors">Contact Us</a></li>
              <li><a href="/privacy" className="hover:text-gray-300 transition-colors">Privacy Policy</a></li>
            </ul>
          </div>
          <div>
            <h3 className="text-xl font-bold mb-4">Follow Us</h3>
            <div className="flex space-x-4">
              <a href="#" className="hover:text-gray-300 transition-colors">Facebook</a>
              <a href="#" className="hover:text-gray-300 transition-colors">Twitter</a>
              <a href="#" className="hover:text-gray-300 transition-colors">LinkedIn</a>
            </div>
          </div>
        </div>
        <div className="border-t border-gray-700 mt-8 pt-8 text-center">
          <p>&copy; 2024 Your Company. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;'''
        else:
            return '''import React from 'react';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-grid">
          <div className="footer-column">
            <h3>Company</h3>
            <ul>
              <li><a href="/about">About Us</a></li>
              <li><a href="/careers">Careers</a></li>
              <li><a href="/news">News</a></li>
            </ul>
          </div>
          <div className="footer-column">
            <h3>Services</h3>
            <ul>
              <li><a href="/web-design">Web Design</a></li>
              <li><a href="/development">Development</a></li>
              <li><a href="/consulting">Consulting</a></li>
            </ul>
          </div>
          <div className="footer-column">
            <h3>Support</h3>
            <ul>
              <li><a href="/help">Help Center</a></li>
              <li><a href="/contact">Contact Us</a></li>
              <li><a href="/privacy">Privacy Policy</a></li>
            </ul>
          </div>
          <div className="footer-column">
            <h3>Follow Us</h3>
            <div className="social-links">
              <a href="#">Facebook</a>
              <a href="#">Twitter</a>
              <a href="#">LinkedIn</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2024 Your Company. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;'''
    
    def _generate_generic_react_component(self, component_name: str, analysis: Dict) -> str:
        """Generate generic React component"""
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        
        if css_framework == "tailwind":
            return f'''import React from 'react';

const {component_name.capitalize()} = () => {{
  return (
    <div className="py-8 px-4">
      <div className="container mx-auto">
        <h2 className="text-3xl font-bold text-center mb-8">
          {component_name.capitalize()}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {{/* Add your {component_name} content here */}}
        </div>
      </div>
    </div>
  );
}};

export default {component_name.capitalize()};'''
        else:
            return f'''import React from 'react';
import './{component_name.capitalize()}.css';

const {component_name.capitalize()} = () => {{
  return (
    <div className="{component_name.lower()}">
      <div className="container">
        <h2>{component_name.capitalize()}</h2>
        <div className="content">
          {{/* Add your {component_name} content here */}}
        </div>
      </div>
    </div>
  );
}};

export default {component_name.capitalize()};'''
    
    async def _generate_next_component(self, component_name: str, analysis: Dict) -> str:
        """Generate Next.js component (similar to React but with Next.js specific features)"""
        # Next.js components are essentially React components with some Next.js features
        react_component = await self._generate_react_component(component_name, analysis)
        
        # Add Next.js specific imports if needed
        if "Link" in react_component:
            react_component = react_component.replace(
                "import { Link } from 'react-router-dom';",
                "import Link from 'next/link';"
            )
        
        return react_component
    
    async def _generate_vue_component(self, component_name: str, analysis: Dict) -> str:
        """Generate Vue component"""
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        
        if component_name.lower() == "header":
            return self._generate_vue_header(analysis)
        elif component_name.lower() == "navigation":
            return self._generate_vue_navigation(analysis)
        else:
            return f'''<template>
  <div class="{'py-8 px-4' if css_framework == 'tailwind' else component_name.lower()}">
    <div class="{'container mx-auto' if css_framework == 'tailwind' else 'container'}">
      <h2 class="{'text-3xl font-bold text-center mb-8' if css_framework == 'tailwind' else 'title'}">
        {component_name.capitalize()}
      </h2>
      <div class="{'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' if css_framework == 'tailwind' else 'content'}">
        <!-- Add your {component_name} content here -->
      </div>
    </div>
  </div>
</template>

<script>
export default {{
  name: '{component_name.capitalize()}',
  data() {{
    return {{
      // Component data
    }}
  }},
  methods: {{
    // Component methods
  }}
}}
</script>

<style scoped>
/* Component styles */
</style>'''
    
    def _generate_vue_header(self, analysis: Dict) -> str:
        """Generate Vue Header component"""
        return '''<template>
  <header class="header">
    <div class="header-container">
      <div class="header-content">
        <div class="logo">
          <div class="logo-text">Your Logo</div>
        </div>
        
        <Navigation />
        
        <div class="mobile-menu-button">
          <button @click="toggleMenu" class="menu-toggle">
            ☰
          </button>
        </div>
      </div>
      
      <div v-if="isMenuOpen" class="mobile-menu">
        <Navigation :mobile="true" />
      </div>
    </div>
  </header>
</template>

<script>
import Navigation from './Navigation.vue'

export default {
  name: 'Header',
  components: {
    Navigation
  },
  data() {
    return {
      isMenuOpen: false
    }
  },
  methods: {
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen
    }
  }
}
</script>

<style scoped>
.header {
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  position: fixed;
  width: 100%;
  top: 0;
  z-index: 50;
}

.header-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-text {
  font-size: 1.5rem;
  font-weight: bold;
  color: #1f2937;
}

.menu-toggle {
  display: none;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
}

@media (max-width: 768px) {
  .menu-toggle {
    display: block;
  }
}
</style>'''
    
    async def _generate_angular_component(self, component_name: str, analysis: Dict) -> str:
        """Generate Angular component"""
        return f'''import {{ Component }} from '@angular/core';

@Component({{
  selector: 'app-{component_name.lower()}',
  template: `
    <div class="{component_name.lower()}">
      <div class="container">
        <h2>{component_name.capitalize()}</h2>
        <div class="content">
          <!-- Add your {component_name} content here -->
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./{component_name.lower()}.component.css']
}})
export class {component_name.capitalize()}Component {{
  title = '{component_name.capitalize()}';
  
  constructor() {{ }}
  
  ngOnInit(): void {{
    // Component initialization
  }}
}}'''
    
    async def _generate_vanilla_component(self, component_name: str, analysis: Dict) -> str:
        """Generate vanilla HTML/CSS/JS component"""
        return f'''<!-- {component_name.capitalize()} Component -->
<div class="{component_name.lower()}" id="{component_name.lower()}">
  <div class="container">
    <h2>{component_name.capitalize()}</h2>
    <div class="content">
      <!-- Add your {component_name} content here -->
    </div>
  </div>
</div>

<script>
class {component_name.capitalize()} {{
  constructor(element) {{
    this.element = element;
    this.init();
  }}
  
  init() {{
    // Component initialization
  }}
}}

// Initialize component
document.addEventListener('DOMContentLoaded', function() {{
  const {component_name.lower()}Element = document.getElementById('{component_name.lower()}');
  if ({component_name.lower()}Element) {{
    new {component_name.capitalize()}({component_name.lower()}Element);
  }}
}});
</script>'''
    
    async def _generate_pages(self, analysis: Dict, framework: str) -> Dict[str, str]:
        """Generate pages/routes based on framework"""
        pages = {}
        
        if framework == "react":
            pages["src/App.js"] = self._generate_react_app(analysis)
            pages["src/pages/Home.js"] = self._generate_react_home_page(analysis)
            # Minimal About.js fallback
            pages["src/pages/About.js"] = "import React from 'react';\n\nconst About = () => (\n  <div className='about'>\n    <h2>About</h2>\n    <p>This is the About page.</p>\n  </div>\n);\n\nexport default About;"
            pages["src/index.js"] = self._generate_react_index()
            
        elif framework == "next":
            pages["pages/index.js"] = self._generate_next_home_page(analysis)
            pages["pages/about.js"] = self._generate_next_about_page(analysis)
            pages["pages/_app.js"] = self._generate_next_app(analysis)
            pages["pages/_document.js"] = self._generate_next_document()
            
        elif framework == "vue":
            pages["src/App.vue"] = self._generate_vue_app(analysis)
            pages["src/views/Home.vue"] = self._generate_vue_home_page(analysis)
            pages["src/views/About.vue"] = self._generate_vue_about_page(analysis)
            pages["src/main.js"] = self._generate_vue_main()
            
        elif framework == "vanilla":
            pages["index.html"] = self._generate_vanilla_html(analysis)
            pages["about.html"] = self._generate_vanilla_about_html(analysis)
            pages["js/main.js"] = self._generate_vanilla_js(analysis)
        
        return pages
    
    def _generate_react_app(self, analysis: Dict) -> str:
        """Generate React App.js"""
        components = analysis.get("components", [])
        
        imports = []
        component_usage = []
        
        for component in components:
            comp_name = component.capitalize()
            imports.append(f"import {comp_name} from './components/{comp_name}';")
            component_usage.append(f"      <{comp_name} />")
        
        return f'''import React from 'react';
import {{ BrowserRouter as Router, Routes, Route }} from 'react-router-dom';
{chr(10).join(imports)}
import Home from './pages/Home';
import About from './pages/About';
import './App.css';

function App() {{
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={{<Home />}} />
          <Route path="/about" element={{<About />}} />
        </Routes>
      </div>
    </Router>
  );
}}

export default App;'''
    
    def _generate_react_home_page(self, analysis: Dict) -> str:
        """Generate React Home page"""
        components = analysis.get("components", [])
        
        imports = []
        component_usage = []
        
        for component in components:
            comp_name = component.capitalize()
            imports.append(f"import {comp_name} from '../components/{comp_name}';")
            component_usage.append(f"      <{comp_name} />")
        
        return f'''import React from 'react';
{chr(10).join(imports)}

const Home = () => {{
  return (
    <div className="home">
{chr(10).join(component_usage)}
    </div>
  );
}};

export default Home;'''
    
    def _generate_react_index(self) -> str:
        """Generate React index.js"""
        return '''import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);'''
    
    async def _generate_styles(self, analysis: Dict, framework: str) -> Dict[str, str]:
        """Generate CSS/style files"""
        styles = {}
        colors = analysis.get("colors", {})
        typography = analysis.get("typography", {})
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        
        if css_framework == "tailwind":
            styles["tailwind.config.js"] = self._generate_tailwind_config(analysis)
            styles["src/index.css"] = self._generate_tailwind_css()
        else:
            styles["src/index.css"] = self._generate_global_css(analysis)
            styles["src/components.css"] = self._generate_component_css(analysis)
        
        return styles
    
    def _generate_tailwind_config(self, analysis: Dict) -> str:
        """Generate Tailwind CSS configuration"""
        colors = analysis.get("colors", {})
        
        return f'''module.exports = {{
  content: [
    "./src/**/*.{{js,jsx,ts,tsx}}",
    "./public/index.html",
  ],
  theme: {{
    extend: {{
      colors: {{
        primary: "{colors.get('primary', '#3b82f6')}",
        secondary: "{colors.get('secondary', '#64748b')}",
        accent: "{colors.get('accent', '#8b5cf6')}",
      }},
      fontFamily: {{
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Georgia', 'serif'],
      }},
    }},
  }},
  plugins: [],
}}'''
    
    def _generate_tailwind_css(self) -> str:
        """Generate Tailwind CSS base styles"""
        return '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    scroll-behavior: smooth;
  }
  
  body {
    font-family: 'Inter', system-ui, sans-serif;
    line-height: 1.6;
  }
}

@layer components {
  .btn {
    @apply px-6 py-2 rounded-lg font-medium transition-colors duration-200;
  }
  
  .btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700;
  }
  
  .btn-secondary {
    @apply bg-gray-600 text-white hover:bg-gray-700;
  }
  
  .container {
    @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8;
  }
}'''
    
    def _generate_global_css(self, analysis: Dict) -> str:
        """Generate global CSS styles"""
        colors = analysis.get("colors", {})
        typography = analysis.get("typography", {})
        
        return f'''/* Global Styles */
* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

html {{
  scroll-behavior: smooth;
}}

body {{
  font-family: {typography.get('primary', 'Inter, system-ui, sans-serif')};
  line-height: 1.6;
  color: {colors.get('text', '#333333')};
  background-color: {colors.get('background', '#ffffff')};
}}

.container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}}

/* Typography */
h1, h2, h3, h4, h5, h6 {{
  font-weight: bold;
  margin-bottom: 1rem;
  color: {colors.get('heading', '#1a1a1a')};
}}

h1 {{ font-size: 2.5rem; }}
h2 {{ font-size: 2rem; }}
h3 {{ font-size: 1.75rem; }}
h4 {{ font-size: 1.5rem; }}
h5 {{ font-size: 1.25rem; }}
h6 {{ font-size: 1rem; }}

p {{
  margin-bottom: 1rem;
}}

/* Links */
a {{
  color: {colors.get('primary', '#3b82f6')};
  text-decoration: none;
  transition: color 0.2s ease;
}}

a:hover {{
  color: {colors.get('secondary', '#1e40af')};
}}

/* Buttons */
.btn {{
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
}}

.btn-primary {{
  background-color: {colors.get('primary', '#3b82f6')};
  color: white;
}}

.btn-primary:hover {{
  background-color: {colors.get('primary_hover', '#2563eb')};
}}

.btn-secondary {{
  background-color: {colors.get('secondary', '#64748b')};
  color: white;
}}

.btn-secondary:hover {{
  background-color: {colors.get('secondary_hover', '#475569')};
}}

/* Utilities */
.text-center {{ text-align: center; }}
.text-left {{ text-align: left; }}
.text-right {{ text-align: right; }}

.mb-4 {{ margin-bottom: 1rem; }}
.mb-8 {{ margin-bottom: 2rem; }}
.mt-4 {{ margin-top: 1rem; }}
.mt-8 {{ margin-top: 2rem; }}

.py-4 {{ padding: 1rem 0; }}
.py-8 {{ padding: 2rem 0; }}
.px-4 {{ padding: 0 1rem; }}

/* Responsive */
@media (max-width: 768px) {{
  .container {{
    padding: 0 0.5rem;
  }}
  
  h1 {{ font-size: 2rem; }}
  h2 {{ font-size: 1.75rem; }}
  h3 {{ font-size: 1.5rem; }}
}}'''
    
    def _generate_component_css(self, analysis: Dict) -> str:
        """Generate component-specific CSS"""
        colors = analysis.get("colors", {})
        
        return f'''/* Component Styles */

/* Header */
.header {{
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  position: fixed;
  width: 100%;
  top: 0;
  z-index: 1000;
}}

.header-container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}}

.header-content {{
  display: flex;
  align-items: center;
  justify-content: space-between;
}}

.logo-text {{
  font-size: 1.5rem;
  font-weight: bold;
  color: {colors.get('primary', '#1f2937')};
}}

/* Navigation */
.navigation {{
  display: flex;
  align-items: center;
  gap: 2rem;
}}

.navigation.mobile {{
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}}

.nav-link {{
  color: {colors.get('text', '#374151')};
  font-weight: 500;
  transition: color 0.2s ease;
}}

.nav-link:hover {{
  color: {colors.get('primary', '#3b82f6')};
}}

.menu-toggle {{
  display: none;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
}}

/* Hero */
.hero {{
  background: linear-gradient(135deg, {colors.get('primary', '#3b82f6')} 0%, {colors.get('accent', '#8b5cf6')} 100%);
  color: white;
  padding: 5rem 1rem;
  margin-top: 4rem;
  text-align: center;
}}

.hero-container {{
  max-width: 1200px;
  margin: 0 auto;
}}

.hero-title {{
  font-size: 3rem;
  font-weight: bold;
  margin-bottom: 1.5rem;
}}

.hero-subtitle {{
  font-size: 1.25rem;
  margin-bottom: 2rem;
  opacity: 0.9;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}}

.hero-buttons {{
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}}

/* Footer */
.footer {{
  background-color: {colors.get('dark', '#1f2937')};
  color: white;
  padding: 3rem 0;
}}

.footer-container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}}

.footer-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}}

.footer-column h3 {{
  font-size: 1.25rem;
  font-weight: bold;
  margin-bottom: 1rem;
  color: white;
}}

.footer-column ul {{
  list-style: none;
}}

.footer-column li {{
  margin-bottom: 0.5rem;
}}

.footer-column a {{
  color: #d1d5db;
  transition: color 0.2s ease;
}}

.footer-column a:hover {{
  color: white;
}}

.footer-bottom {{
  border-top: 1px solid #374151;
  padding-top: 2rem;
  text-align: center;
  color: #9ca3af;
}}

.social-links {{
  display: flex;
  gap: 1rem;
}}

/* Responsive */
@media (max-width: 768px) {{
  .menu-toggle {{
    display: block;
  }}
  
  .navigation:not(.mobile) {{
    display: none;
  }}
  
  .hero-title {{
    font-size: 2rem;
  }}
  
  .hero-buttons {{
    flex-direction: column;
    align-items: center;
  }}
  
  .footer-grid {{
    grid-template-columns: 1fr;
  }}
}}'''
    
    async def _generate_utilities(self, analysis: Dict, framework: str) -> Dict[str, str]:
        """Generate utility files and helpers"""
        utilities = {}
        
        if framework in ["react", "next"]:
            utilities["src/utils/helpers.js"] = self._generate_js_helpers()
            utilities["src/utils/constants.js"] = self._generate_constants(analysis)
            utilities["src/hooks/useLocalStorage.js"] = self._generate_local_storage_hook()
            
        elif framework == "vue":
            utilities["src/utils/helpers.js"] = self._generate_js_helpers()
            utilities["src/utils/constants.js"] = self._generate_constants(analysis)
            utilities["src/composables/useLocalStorage.js"] = self._generate_vue_composables()
            
        elif framework == "vanilla":
            utilities["js/utils.js"] = self._generate_vanilla_utils()
            utilities["js/constants.js"] = self._generate_constants(analysis)
        
        return utilities
    
    def _generate_js_helpers(self) -> str:
        """Generate JavaScript helper functions"""
        return '''// Utility Helper Functions

export const formatDate = (date) => {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

export const slugify = (text) => {
  return text
    .toString()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\-]+/g, '')
    .replace(/\-\-+/g, '-')
    .replace(/^-+/, '')
    .replace(/-+$/, '');
};

export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

export const throttle = (func, limit) => {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

export const scrollToElement = (elementId, offset = 0) => {
  const element = document.getElementById(elementId);
  if (element) {
    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;
    
    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  }
};

export const isInViewport = (element) => {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
};

export const getRandomId = () => {
  return Math.random().toString(36).substr(2, 9);
};

export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export const capitalizeFirst = (str) => {
  return str.charAt(0).toUpperCase() + str.slice(1);
};

export const truncateText = (text, length) => {
  if (text.length <= length) return text;
  return text.substring(0, length) + '...';
};'''
    
    def _generate_constants(self, analysis: Dict) -> str:
        """Generate constants file"""
        colors = analysis.get("colors", {})
        
        return f'''// Application Constants

export const COLORS = {{
  PRIMARY: '{colors.get("primary", "#3b82f6")}',
  SECONDARY: '{colors.get("secondary", "#64748b")}',
  ACCENT: '{colors.get("accent", "#8b5cf6")}',
  SUCCESS: '#10b981',
  WARNING: '#f59e0b',
  ERROR: '#ef4444',
  GRAY: {{
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  }}
}};

export const BREAKPOINTS = {{
  SM: '640px',
  MD: '768px',
  LG: '1024px',
  XL: '1280px',
  '2XL': '1536px'
}};

export const ANIMATIONS = {{
  FAST: '150ms',
  NORMAL: '300ms',
  SLOW: '500ms'
}};

export const API_ENDPOINTS = {{
  BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:3001',
  CONTACT: '/api/contact',
  NEWSLETTER: '/api/newsletter'
}};

export const SOCIAL_LINKS = {{
  FACEBOOK: '#',
  TWITTER: '#',
  LINKEDIN: '#',
  INSTAGRAM: '#'
}};

export const NAVIGATION_ITEMS = [
  {{ name: 'Home', href: '/', external: false }},
  {{ name: 'About', href: '/about', external: false }},
  {{ name: 'Services', href: '/services', external: false }},
  {{ name: 'Contact', href: '/contact', external: false }}
];'''
    
    def _generate_local_storage_hook(self) -> str:
        """Generate React localStorage hook"""
        return '''import { useState, useEffect } from 'react';

export const useLocalStorage = (key, initialValue) => {
  // Get value from localStorage or use initial value
  const [storedValue, setStoredValue] = useState(() => {
    if (typeof window === "undefined") {
      return initialValue;
    }
    
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.log(error);
      return initialValue;
    }
  });

  // Return a wrapped version of useState's setter function that persists the new value to localStorage
  const setValue = (value) => {
    try {
      // Allow value to be a function so we have the same API as useState
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      
      // Save to localStorage
      if (typeof window !== "undefined") {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.log(error);
    }
  };

  return [storedValue, setValue];
};'''
    
    def _generate_vue_composables(self) -> str:
        """Generate Vue composables"""
        return '''import { ref, watch } from 'vue'

export function useLocalStorage(key, defaultValue) {
  const storedValue = ref(defaultValue)

  // Read value from localStorage on initialization
  if (typeof window !== 'undefined') {
    try {
      const item = window.localStorage.getItem(key)
      if (item) {
        storedValue.value = JSON.parse(item)
      }
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error)
    }
  }

  // Watch for changes and update localStorage
  watch(
    storedValue,
    (newValue) => {
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(key, JSON.stringify(newValue))
        } catch (error) {
          console.warn(`Error setting localStorage key "${key}":`, error)
        }
      }
    },
    { deep: true }
  )

  return storedValue
}

export function useToggle(initialValue = false) {
  const value = ref(initialValue)

  const toggle = () => {
    value.value = !value.value
  }

  const setTrue = () => {
    value.value = true
  }

  const setFalse = () => {
    value.value = false
  }

  return {
    value,
    toggle,
    setTrue,
    setFalse
  }
}'''
    
    def _generate_vanilla_utils(self) -> str:
        """Generate vanilla JavaScript utilities"""
        return '''// Vanilla JavaScript Utilities

class Utils {
  static formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }
  
  static debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
  
  static scrollToElement(elementId, offset = 0) {
    const element = document.getElementById(elementId);
    if (element) {
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - offset;
      
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  }
  
  static validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }
  
  static addClass(element, className) {
    if (element && !element.classList.contains(className)) {
      element.classList.add(className);
    }
  }
  
  static removeClass(element, className) {
    if (element && element.classList.contains(className)) {
      element.classList.remove(className);
    }
  }
  
  static toggleClass(element, className) {
    if (element) {
      element.classList.toggle(className);
    }
  }
}

// Export for use in other files
window.Utils = Utils;'''
    
    def _generate_package_json(self, analysis: Dict, framework: str) -> Dict:
        """Generate package.json based on framework"""
        base_package = {
            "name": "generated-website",
            "version": "1.0.0",
            "description": "Generated website clone",
            "main": "index.js",
            "scripts": {},
            "dependencies": {},
            "devDependencies": {}
        }
        
        if framework == "react":
            base_package.update({
                "scripts": {
                    "start": "react-scripts start",
                    "build": "react-scripts build",
                    "test": "react-scripts test",
                    "eject": "react-scripts eject"
                },
                "dependencies": {
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                    "react-router-dom": "^6.8.0",
                    "react-scripts": "5.0.1"
                },
                "devDependencies": {
                    "tailwindcss": "^3.2.0",
                    "autoprefixer": "^10.4.0",
                    "postcss": "^8.4.0"
                }
            })
            
        elif framework == "next":
            base_package.update({
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                    "lint": "next lint"
                },
                "dependencies": {
                    "next": "^13.1.0",
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0"
                },
                "devDependencies": {
                    "tailwindcss": "^3.2.0",
                    "autoprefixer": "^10.4.0",
                    "postcss": "^8.4.0",
                    "eslint": "^8.0.0",
                    "eslint-config-next": "^13.1.0"
                }
            })
            
        elif framework == "vue":
            base_package.update({
                "scripts": {
                    "serve": "vue-cli-service serve",
                    "build": "vue-cli-service build",
                    "lint": "vue-cli-service lint"
                },
                "dependencies": {
                    "vue": "^3.2.0",
                    "vue-router": "^4.1.0"
                },
                "devDependencies": {
                    "@vue/cli-service": "^5.0.0",
                    "tailwindcss": "^3.2.0",
                    "autoprefixer": "^10.4.0",
                    "postcss": "^8.4.0"
                }
            })
            
        elif framework == "angular":
            base_package.update({
                "scripts": {
                    "ng": "ng",
                    "start": "ng serve",
                    "build": "ng build",
                    "test": "ng test",
                    "lint": "ng lint"
                },
                "dependencies": {
                    "@angular/core": "^15.0.0",
                    "@angular/common": "^15.0.0",
                    "@angular/platform-browser": "^15.0.0",
                    "@angular/router": "^15.0.0"
                },
                "devDependencies": {
                    "@angular/cli": "^15.0.0",
                    "@angular/compiler-cli": "^15.0.0",
                    "typescript": "^4.8.0"
                }
            })
        
        elif framework == "vanilla":
            base_package.update({
                "scripts": {
                    "start": "serve ."
                },
                "dependencies": {
                    "serve": "^14.2.0"
                }
            })
        
        return base_package
    
    def _generate_config_files(self, analysis: Dict, framework: str) -> Dict[str, str]:
        """Generate configuration files"""
        config_files = {}
        
        # Generate common config files
        config_files[".gitignore"] = self._generate_gitignore(framework)
        config_files["README.md"] = self._generate_readme(framework)
        
        if framework in ["react", "next", "vue"]:
            config_files["postcss.config.js"] = self._generate_postcss_config()
        
        if framework == "next":
            config_files["next.config.js"] = self._generate_next_config()
            
        elif framework == "vue":
            config_files["vue.config.js"] = self._generate_vue_config()
            
        elif framework == "angular":
            config_files["angular.json"] = self._generate_angular_config()
            config_files["tsconfig.json"] = self._generate_typescript_config()
        
        return config_files
    
    def _generate_gitignore(self, framework: str) -> str:
        """Generate .gitignore file"""
        base_ignore = """# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Production builds
/build
/dist
/.next
/out

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# IDE and editor files
.vscode/
.idea/
*.swp
*.swo

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
logs
*.log

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/

# Temporary folders
tmp/
temp/"""

        if framework == "angular":
            base_ignore += """

# Angular specific
/e2e
/coverage
/.nyc_output"""

        return base_ignore
    
    def _generate_readme(self, framework: str) -> str:
        """Generate README.md file"""
        return f"""# Generated Website Clone

This is a website clone generated using the Generator Agent.

## Framework
- **{framework.capitalize()}**

## Getting Started

### Prerequisites
- Node.js (v14 or higher)
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm {'run dev' if framework == 'next' else 'start' if framework == 'react' else 'run serve' if framework == 'vue' else 'start'}
```

3. Open your browser to `http://localhost:3000`

### Building for Production

```bash
npm run build
```

## Project Structure

```
src/
├── components/     # Reusable components
├── pages/         # Page components
├── utils/         # Utility functions
└── styles/        # CSS styles
```

## Features

- Responsive design
- Modern UI components
- Optimized performance
- Cross-browser compatibility

## Technologies Used

- {framework.capitalize()}
- CSS3/Tailwind CSS
- Modern JavaScript (ES6+)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.
"""
    
    def _generate_postcss_config(self) -> str:
        """Generate PostCSS configuration"""
        return """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}"""
    
    def _generate_next_config(self) -> str:
        """Generate Next.js configuration"""
        return """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: [],
  },
  experimental: {
    appDir: false,
  },
}

module.exports = nextConfig"""
    
    def _generate_vue_config(self) -> str:
        """Generate Vue configuration"""
        return """const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  css: {
    loaderOptions: {
      postcss: {
        postcssOptions: {
          plugins: [
            require('tailwindcss'),
            require('autoprefixer'),
          ],
        },
      },
    },
  },
})"""
    
    def _generate_deployment_config(self, framework: str) -> Dict:
        """Generate deployment configuration"""
        config = {
            "vercel": {
                "name": "generated-website",
                "version": 2,
                "builds": []
            },
            "netlify": {
                "build": {
                    "command": "npm run build",
                    "publish": ""
                }
            }
        }
        
        if framework == "react":
            config["vercel"]["builds"] = [{"src": "package.json", "use": "@vercel/static-build"}]
            config["netlify"]["build"]["publish"] = "build"
            
        elif framework == "next":
            config["vercel"]["builds"] = [{"src": "next.config.js", "use": "@vercel/next"}]
            config["netlify"]["build"]["publish"] = ".next"
            
        elif framework == "vue":
            config["vercel"]["builds"] = [{"src": "package.json", "use": "@vercel/static-build"}]
            config["netlify"]["build"]["publish"] = "dist"
        
        return config
    
    def _generate_commands(self, framework: str) -> tuple:
        """Generate build and dev commands"""
        commands = {
            "react": {
                "build": ["npm run build"],
                "dev": ["npm start"]
            },
            "next": {
                "build": ["npm run build"],
                "dev": ["npm run dev"]
            },
            "vue": {
                "build": ["npm run build"],
                "dev": ["npm run serve"]
            },
            "angular": {
                "build": ["ng build --prod"],
                "dev": ["ng serve"]
            },
            "vanilla": {
                "build": ["# No build step required for vanilla HTML/CSS/JS"],
                "dev": ["# Serve files using a local server like http-server"]
            }
        }
        
        return commands[framework]["build"], commands[framework]["dev"]
    
    def _extract_assets(self, analysis: Dict) -> List[str]:
        """Extract asset requirements from analysis"""
        assets = []
        
        # Extract from analysis
        if "assets" in analysis:
            assets.extend(analysis["assets"])
        
        # Common assets for web projects
        assets.extend([
            "favicon.ico",
            "logo.png",
            "hero-image.jpg",
            "placeholder-image.jpg"
        ])
        
        return list(set(assets))  # Remove duplicates
    
    def _get_file_extension(self, framework: str) -> str:
        """Get appropriate file extension for framework"""
        extensions = {
            "react": "jsx",
            "next": "jsx",
            "vue": "vue",
            "angular": "component.ts",
            "vanilla": "html"
        }

        return extensions.get(framework, "jsx")

    def _get_react_template(self) -> Dict:
        """Return React project template structure"""
        return {
            "src": {
                "components": ["Header.jsx", "Navigation.jsx", "Hero.jsx", "Footer.jsx"],
                "pages": ["Home.jsx", "About.jsx"],
                "utils": ["helpers.js", "constants.js"],
                "App.jsx": "",
                "index.jsx": "",
                "index.css": ""
            },
            "public": ["index.html", "favicon.ico"],
            "package.json": "",
            ".gitignore": "",
            "README.md": "",
            "postcss.config.js": "",
            "tailwind.config.js": ""
        }

    def _get_nextjs_template(self) -> Dict:
        """Return Next.js project template structure"""
        return {
            "pages": ["index.jsx", "about.jsx", "_app.jsx", "_document.jsx"],
            "components": ["Header.jsx", "Navigation.jsx", "Hero.jsx", "Footer.jsx"],
            "public": ["favicon.ico", "images/"],
            "styles": ["globals.css"],
            "package.json": "",
            "next.config.js": "",
            ".gitignore": "",
            "README.md": "",
            "postcss.config.js": "",
            "tailwind.config.js": ""
        }

    def _get_vue_template(self) -> Dict:
        """Return Vue project template structure"""
        return {
            "src": {
                "components": ["Header.vue", "Navigation.vue", "Hero.vue", "Footer.vue"],
                "views": ["Home.vue", "About.vue"],
                "utils": ["helpers.js", "constants.js"],
                "App.vue": "",
                "main.js": "",
                "assets": ["logo.png"]
            },
            "public": ["index.html", "favicon.ico"],
            "package.json": "",
            ".gitignore": "",
            "README.md": "",
            "vue.config.js": "",
            "tailwind.config.js": ""
        }

    def _get_angular_template(self) -> Dict:
        """Return Angular project template structure"""
        return {
            "src": {
                "app": {
                    "components": [
                        "header.component.ts",
                        "navigation.component.ts",
                        "hero.component.ts",
                        "footer.component.ts"
                    ],
                    "pages": [
                        "home.component.ts",
                        "about.component.ts"
                    ],
                    "app.component.ts": "",
                    "app.module.ts": "",
                    "app-routing.module.ts": ""
                },
                "assets": [],
                "styles.css": ""
            },
            "angular.json": "",
            "tsconfig.json": "",
            "package.json": "",
            ".gitignore": "",
            "README.md": ""
        }

    def _get_vanilla_template(self) -> Dict:
        """Return vanilla HTML/CSS/JS project template structure"""
        return {
            "": ["index.html", "about.html"],
            "css": ["styles.css", "components.css"],
            "js": ["main.js", "utils.js", "constants.js"],
            "assets": ["favicon.ico", "logo.png"],
            ".gitignore": "",
            "README.md": ""
        }

    def _generate_react_forms(self, analysis: Dict) -> str:
        """Generate React Forms component"""
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        colors = analysis.get("colors", {})

        if css_framework == "tailwind":
            primary_color = colors.get("primary", "#3b82f6").replace("#", "")
            return f'''import React, {{ useState }} from 'react';

const Forms = () => {{
  const [formData, setFormData] = useState({{
    name: '',
    email: '',
    message: ''
  }});

  const handleChange = (e) => {{
    setFormData({{ ...formData, [e.target.name]: e.target.value }});
  }};

  const handleSubmit = (e) => {{
    e.preventDefault();
    // Handle form submission
    console.log('Form submitted:', formData);
  }};

  return (
    <section className="py-16 px-4">
      <div className="container mx-auto max-w-2xl">
        <h2 className="text-3xl font-bold text-center mb-8">Contact Us</h2>
        <form onSubmit={{handleSubmit}} className="space-y-6">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
              Name
            </label>
            <input
              type="text"
              name="name"
              id="name"
              value={{formData.name}}
              onChange={{handleChange}}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-#{primary_color} focus:border-transparent"
              required
            />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              type="email"
              name="email"
              id="email"
              value={{formData.email}}
              onChange={{handleChange}}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-#{primary_color} focus:border-transparent"
              required
            />
          </div>
          <div>
            <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
              Message
            </label>
            <textarea
              name="message"
              id="message"
              value={{formData.message}}
              onChange={{handleChange}}
              rows="4"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-#{primary_color} focus:border-transparent"
              required
            ></textarea>
          </div>
          <button
            type="submit"
            className="w-full bg-#{primary_color} text-white py-3 rounded-lg font-semibold hover:bg-#{self._darken_color(primary_color, 0.8)} transition-colors"
          >
            Send Message
          </button>
        </form>
      </div>
    </section>
  );
}};

export default Forms;'''
        else:
            return f'''import React, {{ useState }} from 'react';
import './Forms.css';

const Forms = () => {{
  const [formData, setFormData] = useState({{
    name: '',
    email: '',
    message: ''
  }});

  const handleChange = (e) => {{
    setFormData({{ ...formData, [e.target.name]: e.target.value }});
  }};

  const handleSubmit = (e) => {{
    e.preventDefault();
    // Handle form submission
    console.log('Form submitted:', formData);
  }};

  return (
    <section className="forms">
      <div className="container">
        <h2>Contact Us</h2>
        <form onSubmit={{handleSubmit}}>
          <div className="form-group">
            <label htmlFor="name">Name</label>
            <input
              type="text"
              name="name"
              id="name"
              value={{formData.name}}
              onChange={{handleChange}}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              name="email"
              id="email"
              value={{formData.email}}
              onChange={{handleChange}}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="message">Message</label>
            <textarea
              name="message"
              id="message"
              value={{formData.message}}
              onChange={{handleChange}}
              rows="4"
              required
            ></textarea>
          </div>
          <button type="submit">Send Message</button>
        </form>
      </div>
    </section>
  );
}};

export default Forms;'''

    def _generate_react_cards(self, analysis: Dict) -> str:
        """Generate React Cards component"""
        css_framework = analysis.get("framework", {}).get("css", "tailwind")
        colors = analysis.get("colors", {})

        if css_framework == "tailwind":
            primary_color = colors.get("primary", "#3b82f6").replace("#", "")
            return f'''import React from 'react';

const Cards = () => {{
  const cardsData = [
    {{
      title: 'Feature One',
      description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
      icon: 'star'
    }},
    {{
      title: 'Feature Two',
      description: 'Sed do eiusmod tempor incididunt ut labore et dolore.',
      icon: 'heart'
    }},
    {{
      title: 'Feature Three',
      description: 'Ut enim ad minim veniam, quis nostrud exercitation.',
      icon: 'rocket'
    }}
  ];

  return (
    <section className="py-16 px-4">
      <div className="container mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12">Our Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {{cardsData.map((card, index) => (
            <div key={{index}} className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow duration-300">
              <div className="w-12 h-12 bg-#{primary_color} rounded-lg mb-4 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-4">{{card.title}}</h3>
              <p className="text-gray-600">{{card.description}}</p>
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}};

export default Cards;'''
        else:
            return f'''import React from 'react';
import './Cards.css';

const Cards = () => {{
  const cardsData = [
    {{
      title: 'Feature One',
      description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
      icon: 'star'
    }},
    {{
      title: 'Feature Two',
      description: 'Sed do eiusmod tempor incididunt ut labore et dolore.',
      icon: 'heart'
    }},
    {{
      title: 'Feature Three',
      description: 'Ut enim ad minim veniam, quis nostrud exercitation.',
      icon: 'rocket'
    }}
  ];

  return (
    <section className="cards">
      <div className="container">
        <h2>Our Features</h2>
        <div className="cards-grid">
          {{cardsData.map((card, index) => (
            <div key={{index}} className="card">
              <div className="card-icon"></div>
              <h3>{{card.title}}</h3>
              <p>{{card.description}}</p>
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}};

export default Cards;'''

    def _generate_next_home_page(self, analysis: Dict) -> str:
        """Generate Next.js Home page"""
        components = analysis.get("components", [])
        imports = []
        component_usage = []

        for component in components:
            comp_name = component.capitalize()
            imports.append(f"import {comp_name} from '../components/{comp_name}';")
            component_usage.append(f"      <{comp_name} />")

        return f'''import Head from 'next/head';
{chr(10).join(imports)}

export default function Home() {{
  return (
    <>
      <Head>
        <title>Generated Website</title>
        <meta name="description" content="AI-generated website clone" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <div className="min-h-screen">
{chr(10).join(component_usage)}
      </div>
    </>
  );
}}'''

    def _generate_next_about_page(self, analysis: Dict) -> str:
        """Generate Next.js About page"""
        return f'''import Head from 'next/head';
import Header from '../components/Header';

export default function About() {{
  return (
    <>
      <Head>
        <title>About | Generated Website</title>
        <meta name="description" content="About page of the AI-generated website" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <div className="min-h-screen">
        <Header />
        <section className="py-16 px-4">
          <div className="container mx-auto">
            <h1 className="text-4xl font-bold text-center mb-8">About Us</h1>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto">
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}}'''

    def _generate_next_app(self, analysis: Dict) -> str:
        """Generate Next.js _app.js"""
        return '''import '../styles/globals.css';

function MyApp({ Component, pageProps }) {
  return <Component {...pageProps} />;
}

export default MyApp;'''

    def _generate_next_document(self) -> str:
        """Generate Next.js _document.js"""
        return '''import Document, { Html, Head, Main, NextScript } from 'next/document';

class MyDocument extends Document {
  render() {
    return (
      <Html lang="en">
        <Head />
        <body>
          <Main />
          <NextScript />
        </body>
      </Html>
    );
  }
}

export default MyDocument;'''

    def _generate_vue_app(self, analysis: Dict) -> str:
        """Generate Vue App.vue"""
        components = analysis.get("components", [])
        imports = []
        component_usage = []

        for component in components:
            comp_name = component.capitalize()
            imports.append(f"import {comp_name} from './components/{comp_name}.vue';")
            component_usage.append(f"    <{comp_name} />")

        return f'''<template>
  <div id="app">
{chr(10).join(component_usage)}
  </div>
</template>

<script>
{chr(10).join(imports)}

export default {{
  name: 'App',
  components: {{
{', '.join([comp.capitalize() for comp in components])}
  }}
}}
</script>

<style>
#app {{
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}
</style>'''

    def _generate_vue_home_page(self, analysis: Dict) -> str:
        """Generate Vue Home page"""
        components = analysis.get("components", [])
        imports = []
        component_usage = []

        for component in components:
            comp_name = component.capitalize()
            imports.append(f"import {comp_name} from '../components/{comp_name}.vue';")
            component_usage.append(f"    <{comp_name} />")

        return f'''<template>
  <div class="home">
{chr(10).join(component_usage)}
  </div>
</template>

<script>
{chr(10).join(imports)}

export default {{
  name: 'Home',
  components: {{
{', '.join([comp.capitalize() for comp in components])}
  }}
}}
</script>

<style scoped>
.home {{
  min-height: 100vh;
}}
</style>'''

    def _generate_vue_navigation(self, analysis: Dict) -> str:
        """Generate Vue Navigation component"""
        css_framework = analysis.get("framework", {}).get("css", "tailwind")

        if css_framework == "tailwind":
            return f'''<template>
  <nav :class="[mobile ? 'flex flex-col space-y-2' : 'hidden md:flex items-center space-x-8']">
    <router-link
      v-for="item in navItems"
      :key="item.name"
      :to="item.href"
      :class="[mobile ? 'block py-2 px-4 text-gray-700 hover:bg-gray-100 rounded transition-colors' : 'text-gray-700 hover:text-blue-600 transition-colors font-medium']"
    >
      {{ item.name }}
    </router-link>
  </nav>
</template>

<script>
export default {{
  name: 'Navigation',
  props: {{
    mobile: {{
      type: Boolean,
      default: false
    }}
  }},
  data() {{
    return {{
      navItems: [
        {{ name: 'Home', href: '/' }},
        {{ name: 'About', href: '/about' }},
        {{ name: 'Services', href: '/services' }},
        {{ name: 'Contact', href: '/contact' }}
      ]
    }}
  }}
}}
</script>'''
        else:
            return f'''<template>
  <nav :class="['navigation', {{ 'mobile': mobile }}]">
    <router-link
      v-for="item in navItems"
      :key="item.name"
      :to="item.href"
      class="nav-link"
    >
      {{ item.name }}
    </router-link>
  </nav>
</template>

<script>
export default {{
  name: 'Navigation',
  props: {{
    mobile: {{
      type: Boolean,
      default: false
    }}
  }},
  data() {{
    return {{
      navItems: [
        {{ name: 'Home', href: '/' }},
        {{ name: 'About', href: '/about' }},
        {{ name: 'Services', href: '/services' }},
        {{ name: 'Contact', href: '/contact' }}
      ]
    }}
  }}
}}
</script>

<style scoped>
.navigation {{
  display: flex;
  align-items: center;
  gap: 2rem;
}}

.navigation.mobile {{
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}}

.nav-link {{
  color: #374151;
  font-weight: 500;
  transition: color 0.2s ease;
}}

.nav-link:hover {{
  color: #3b82f6;
}}
</style>'''

    def _generate_vue_main(self) -> str:
        """Generate Vue main.js"""
        return '''import { createApp } from 'vue';
import App from './App.vue';
import router from './router';

import './index.css';

const app = createApp(App);
app.use(router);
app.mount('#app');'''

    def _generate_vue_about_page(self, analysis: Dict) -> str:
        """Generate Vue About page"""
        return '''<template>
  <div class="about">
    <Header />
    <section class="py-16 px-4">
      <div class="container mx-auto">
        <h1 class="text-4xl font-bold text-center mb-8">About Us</h1>
        <p class="text-lg text-gray-600 max-w-3xl mx-auto">
          Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
        </p>
      </div>
    </section>
  </div>
</template>

<script>
import Header from '../components/Header.vue';

export default {
  name: 'About',
  components: {
    Header
  }
}
</script>

<style scoped>
.about {
  min-height: 100vh;
}
</style>'''

    def _generate_vanilla_html(self, analysis: Dict) -> str:
        """Generate vanilla HTML index page"""
        components = analysis.get("components", [])
        component_usage = []

        for component in components:
            component_usage.append(f'    <div class="{component.lower()}"></div>')

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated Website</title>
  <link rel="stylesheet" href="css/styles.css">
  <link rel="icon" href="assets/favicon.ico">
</head>
<body>
{chr(10).join(component_usage)}
  <script src="js/main.js"></script>
</body>
</html>'''

    def _generate_vanilla_about_html(self, analysis: Dict) -> str:
        """Generate vanilla HTML About page"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>About | Generated Website</title>
  <link rel="stylesheet" href="css/styles.css">
  <link rel="icon" href="assets/favicon.ico">
</head>
<body>
  <div class="header"></div>
  <section class="about">
    <div class="container">
      <h1>About Us</h1>
      <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
    </div>
  </section>
  <script src="js/main.js"></script>
</body>
</html>'''

    def _generate_vanilla_js(self, analysis: Dict) -> str:
        """Generate vanilla JavaScript main file"""
        return '''// Main JavaScript File
document.addEventListener('DOMContentLoaded', () => {
  // Initialize components
  const components = document.querySelectorAll('.header, .navigation, .hero, .footer');
  
  components.forEach(component => {
    // Add component-specific initialization here
    component.classList.add('initialized');
  });
});

// Mobile menu toggle
const menuToggle = document.querySelector('.menu-toggle');
const navigation = document.querySelector('.navigation');

if (menuToggle && navigation) {
  menuToggle.addEventListener('click', () => {
    navigation.classList.toggle('active');
  });
}'''

    def _generate_angular_config(self) -> str:
        """Generate Angular configuration file"""
        return '''{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "newProjectRoot": "projects",
  "projects": {
    "generated-website": {
      "projectType": "application",
      "schematics": {},
      "root": "",
      "sourceRoot": "src",
      "prefix": "app",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "dist/generated-website",
            "index": "src/index.html",
            "main": "src/main.ts",
            "polyfills": "src/polyfills.ts",
            "tsConfig": "tsconfig.app.json",
            "assets": [
              "src/favicon.ico",
              "src/assets"
            ],
            "styles": [
              "src/styles.css"
            ]
          }
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "options": {
            "browserTarget": "generated-website:build"
          }
        }
      }
    }
  },
  "defaultProject": "generated-website"
}'''

    def _generate_typescript_config(self) -> str:
        """Generate TypeScript configuration for Angular"""
        return '''{
  "compileOnSave": false,
  "compilerOptions": {
    "baseUrl": "src",
    "outDir": "./dist/out-tsc",
    "sourceMap": true,
    "declaration": false,
    "downlevelIteration": true,
    "experimentalDecorators": true,
    "module": "es2020",
    "moduleResolution": "node",
    "importHelpers": true,
    "target": "es2020",
    "typeRoots": [
      "node_modules/@types"
    ],
    "lib": [
      "es2018",
      "dom"
    ]
  },
  "angularCompilerOptions": {
    "enableI18nLegacyMessageIdFormat": false,
    "strictInjectionParameters": true,
    "strictInputAccessModifiers": true,
    "strictTemplates": true
  }
}'''
    def _darken_color(self, hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(int(c * factor) for c in rgb)
        return f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    async def _generate_real_code(self, file_name: str, description: str, framework: str, file_type: str) -> str:
        if not description:
            return f"// No description provided for {file_name}"
        prompt = f"""
You are Bolt, an expert AI assistant and exceptional senior software developer with vast knowledge across multiple programming languages, frameworks, and best practices.

For all components, pages, and styles I ask you to generate, make them beautiful, not cookie-cutter. Make webpages that are fully featured and worthy for production.

By default, use JSX syntax with Tailwind CSS classes, React hooks, and Lucide React for icons. Do not install other packages for UI themes, icons, etc. unless absolutely necessary or I request them.

Use icons from lucide-react for logos.

Use stock photos from unsplash where appropriate, only valid URLs you know exist. Do not download the images, only link to them in image tags.

Use 2 spaces for code indentation.

Generate a {framework} {file_type} named {file_name} with the following description:
{description}

Return only the code, no explanations or comments outside the code. The code should be ready for production use, clean, and idiomatic. If generating a React component, export it as default. If generating a CSS file, include all necessary styles for the described component/page.

If you need to use images, use Unsplash URLs. For icons, use lucide-react.

Do not use any UI libraries or icon sets other than Tailwind CSS and lucide-react unless explicitly requested.

Do not include any explanations, only the code.
"""
        if self.model:
            try:
                response = await self.model.generate_content_async(prompt)
                code = response.text.strip()
                # Remove markdown code block if present
                if code.startswith('```'):
                    code = code.split('```', 2)[-1].strip()
                return code
            except Exception as e:
                self.logger.warning(f"Gemini code generation failed for {file_name}: {e}")
        # Fallback: placeholder
        ext = os.path.splitext(file_name)[1]
        if ext in ['.js', '.jsx', '.ts', '.tsx']:
            return f"// {file_name} for {framework}\n// {description}\nexport default function {os.path.splitext(os.path.basename(file_name))[0].capitalize()}() {{\n  return (<div>{description}</div>);\n}}"
        elif ext in ['.css', '.scss', '.less']:
            return f"/* {file_name} for {framework}\n{description}\n*/"
        elif ext == '.json':
            return description or "{}"
        else:
            return f"# {file_name} for {framework}\n# {description}"
  