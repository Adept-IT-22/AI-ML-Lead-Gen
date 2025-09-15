email_prompts = {
    "funding": {
        'subject': 'Scaling After Funding?',
        'content': """
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>Hi {first_name},</p>
                    
                    <p>Congrats to the <strong>{company_name}</strong> team on raising your <strong>{funding_round}</strong> round!</p>
                    
                    <p>We work with fast-growing AI/ML companies like yours to help scale operations by taking on core but time-consuming tasks such as <em>data annotation</em>. 
                    This lets your team stay focused on building while we handle the rest.</p>
                    
                    <p>Would you be open to a quick chat this week to explore how we can support <strong>{company_name}</strong>’s next phase of growth?</p>
                    
                    <p>For more information on Adept Technologies, kindly visit 
                        <a href="https://www.adept-techno.com" target="_blank"><strong>Our Website</strong></a>
                    </p>
                    
                    <p>Regards,<br>
                    Antony Ngatia,<br>
                    Sales, Adept Technologies</p>
                </body>
            </html>
        """
    },
    "hiring": {
        'subject': 'Help While You Scale',
        'content': """
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>Hi {first_name},</p>
                    
                    <p>I noticed <strong>{company_name}</strong> is expanding the team with roles in <strong>{hiring_area}</strong> — that’s exciting!</p>
                    
                    <p>As you grow, some tasks can start pulling focus from your core engineering/product roadmap. 
                    We specialize in supporting AI/ML companies with services like data annotation, customer engagement, and analytics — 
                    helping teams like yours move faster without the growing pains.</p>
                    
                    <p>Is it worth exploring how we could support <strong>{company_name}</strong> during this scaling phase?</p>
                    
                    <p>For more information on Adept Technologies, kindly visit 
                        <a href="https://www.adept-techno.com" target="_blank"><strong>Our Website</strong></a>
                    </p>
                    
                    <p>Regards,<br>
                    Antony Ngatia,<br>
                    Sales, Adept Technologies</p>
                </body>
            </html>
        """
    },
    "events": {
        'subject': 'Post-Event Connection',
        'content': """
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>Hi {first_name},</p>
                    
                    <p>I came across <strong>{company_name}</strong>’s participation in <strong>{event_name}</strong>.</p>
                    
                    <p>At Adept Technologies, we help AI/ML companies like <strong>{company_name}</strong> accelerate growth by providing 
                    <strong>scalable support services</strong> (data solutions, ML services, customer engagement).</p>
                    
                    <p>Would love to connect and share how we could complement what your team is doing.  
                    Would a 15-min call later this week work?</p>
                    
                    <p>For more information on Adept Technologies, kindly visit 
                        <a href="https://www.adept-techno.com" target="_blank"><strong>Our Website</strong></a>
                    </p>
                    
                    <p>Regards,<br>
                    Antony Ngatia,<br>
                    Sales, Adept Technologies</p>
                </body>
            </html>
        """
    }
}
